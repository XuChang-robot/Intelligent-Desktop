import os
import logging
from typing import Dict, Any, Optional
import sqlite3
import json
import hashlib
import pickle
import numpy as np
import faiss
import ollama
import threading
import time
import subprocess

class HybridTaskPlanCache:
    """缓存系统：使用FAISS向量搜索 + SQLite元数据存储 + Ollama语义匹配"""
    
    def __init__(self, cache_dir: str = "cache", similarity_threshold: float = 0.85, ttl: int = 604800, 
                 max_total_size_mb: int = 1024, max_db_size_mb: int = 512, max_faiss_size_mb: int = 512,
                 max_records: int = 10000, cleanup_interval: int = 3600, cleanup_on_startup: bool = True,
                 embedding_model: str = "nomic-embed-text", llm_client=None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.max_total_size_mb = max_total_size_mb
        self.max_db_size_mb = max_db_size_mb
        self.max_faiss_size_mb = max_faiss_size_mb
        self.max_records = max_records
        self.cleanup_interval = cleanup_interval
        self.cleanup_on_startup = cleanup_on_startup
        self.embedding_model_name = embedding_model
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # 加载缓存配置
        self.cache_key_params = self._load_cache_config()
        
        # 初始化SQLite数据库
        self.db_path = os.path.join(cache_dir, "cache.db")
        self._init_database()
        
        # 初始化FAISS索引
        self.faiss_index_path = os.path.join(cache_dir, "faiss.index")
        self.faiss_index = None
        self.embedding_dim = None
        self._init_faiss()
        
        # 清理线程控制
        self._cleanup_thread = None
        self._cleanup_stop_event = threading.Event()
        
        # 启动时清理
        if self.cleanup_on_startup:
            self.cleanup()
        
        # 启动定时清理线程
        if self.cleanup_interval > 0:
            self._start_cleanup_thread()
    
    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建缓存表（存储embedding向量）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faiss_id INTEGER UNIQUE,
                intent_hash TEXT UNIQUE,
                intent_str TEXT,
                plan TEXT,
                plan_template TEXT,
                entities_template TEXT,
                intent_embedding TEXT,
                embedding_vector BLOB,
                timestamp DATETIME,
                last_accessed DATETIME
            )
        ''')
        
        # 添加新列（如果不存在）
        cursor.execute("PRAGMA table_info(cache)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'intent_embedding' not in columns:
            cursor.execute('ALTER TABLE cache ADD COLUMN intent_embedding TEXT')
            conn.commit()
        if 'embedding_vector' not in columns:
            cursor.execute('ALTER TABLE cache ADD COLUMN embedding_vector BLOB')
            conn.commit()
        if 'last_accessed' not in columns:
            cursor.execute('ALTER TABLE cache ADD COLUMN last_accessed DATETIME')
            conn.commit()
        if 'entities_template' not in columns:
            cursor.execute('ALTER TABLE cache ADD COLUMN entities_template TEXT')
            conn.commit()
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_intent_hash ON cache(intent_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_faiss_id ON cache(faiss_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache(last_accessed)')
        
        conn.commit()
        conn.close()
        self.logger.info(f"SQLite数据库初始化成功: {self.db_path}")
    
    def _init_faiss(self):
        """初始化FAISS索引（使用IndexFlatIP + IndexIDMap，支持删除）"""
        try:
            # 尝试加载已存在的索引
            if os.path.exists(self.faiss_index_path):
                self.faiss_index = faiss.read_index(self.faiss_index_path)
                self.embedding_dim = self.faiss_index.d
                self.logger.info(f"FAISS索引加载成功: {self.faiss_index_path}, 维度: {self.embedding_dim}")
            else:
                # 创建新的索引（使用IndexFlatIP + IndexIDMap，支持删除）
                self.embedding_dim = 768  # nomic-embed-text的默认维度
                
                # 使用IndexIDMap包装IndexFlatIP，支持自定义ID和删除操作
                index = faiss.IndexFlatIP(self.embedding_dim)
                self.faiss_index = faiss.IndexIDMap(index)
                
                self.logger.info(f"FAISS IndexFlatIP + IndexIDMap索引创建成功, 维度: {self.embedding_dim}")
        except Exception as e:
            self.logger.error(f"FAISS索引初始化失败: {e}")
            self.embedding_dim = 768
            index = faiss.IndexFlatIP(self.embedding_dim)
            self.faiss_index = faiss.IndexIDMap(index)
    
    def _save_faiss_index(self):
        """保存FAISS索引到文件"""
        try:
            faiss.write_index(self.faiss_index, self.faiss_index_path)
        except Exception as e:
            self.logger.error(f"保存FAISS索引失败: {e}")
    
    def _intent_to_string(self, intent: Dict[str, Any]) -> str:
        """将意图转换为字符串"""
        parts = []
        for key, value in intent.items():
            if isinstance(value, str):
                parts.append(f"{key}:{value.lower().strip()}")
            else:
                parts.append(f"{key}:{value}")
        return " ".join(parts)
    
    def _extract_template(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """从执行计划中提取模板（忽略具体参数值）"""
        template = {
            "plan": plan.get("plan", ""),
            "steps": []
        }
        
        for step in plan.get("steps", []):
            step_template = {
                "tool": step.get("tool", ""),
                "args_template": list(step.get("args", {}).keys()),
                "description": step.get("description", "")
            }
            template["steps"].append(step_template)
        
        return template
    
    def _template_to_string(self, template: Dict[str, Any]) -> str:
        """将模板转换为字符串（用于embedding）"""
        parts = [template.get("plan", "")]
        for step in template.get("steps", []):
            tool = step.get("tool", "")
            args = ",".join(step.get("args_template", []))
            parts.append(f"{tool}({args})")
        return " ".join(parts)
    
    def _intent_to_template_string(self, intent: Dict[str, Any]) -> str:
        """将intent转换为工具调用模式的字符串（用于embedding）"""
        parts = []
        for key, value in intent.items():
            if key == "intent":
                parts.append(str(value))
            elif key == "entities" and isinstance(value, dict):
                # 对于entities，只保留键，忽略值
                keys = ",".join(value.keys())
                parts.append(f"entities({keys})")
            elif isinstance(value, dict):
                # 对于其他dict，只保留键，忽略值
                keys = ",".join(value.keys())
                parts.append(f"{key}({keys})")
            else:
                parts.append(f"{key}:{value}")
        return " ".join(parts)
    
    def _load_cache_config(self) -> Dict[str, Any]:
        """加载缓存配置文件
        
        Returns:
            缓存关键参数配置
        """
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "system_config", "cache_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.logger.info(f"加载缓存配置: {config_path}")
                    return config.get("cache_key_params", {})
            else:
                self.logger.warning(f"缓存配置文件不存在: {config_path}，使用默认配置")
                return {"global": ["operation"]}
        except Exception as e:
            self.logger.error(f"加载缓存配置失败: {e}，使用默认配置")
            return {"global": ["operation"]}
    
    def _extract_entities_template(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """从intent中提取entities模板
        
        支持两种intent格式：
        1. {"intent": "task", "entities": {...}, "confidence": 0.9}  (LLM原始格式)
        2. {"type": "task", "entities": {...}, "confidence": 0.5}   (intent_parser转换后的格式)
        
        注意：为了区分不同的操作类型，entities_template需要包含关键参数的值（如operation）
        关键参数从配置文件中读取，用户不应该修改
        """
        entities = intent.get("entities", {})
        
        # 从配置中获取关键参数列表
        key_param_names = self.cache_key_params.get("global", ["operation"])
        
        # 提取关键参数的值（用于区分不同的操作类型）
        key_params = {}
        for param_name in key_param_names:
            if param_name in entities:
                key_params[param_name] = entities[param_name]
        
        entities_template = {
            "intent": intent.get("intent") or intent.get("type", ""),
            "entities": {
                "keys": list(entities.keys()),
                "key_params": key_params
            },
            "confidence": intent.get("confidence", 0.0)
        }
        return entities_template
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的embedding向量（归一化）"""
        try:
            response = ollama.embeddings(model=self.embedding_model_name, prompt=text)
            embedding = response['embedding']
            
            # 更新维度信息
            if self.embedding_dim is None:
                self.embedding_dim = len(embedding)
                # 重新创建索引
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            
            # 归一化向量，使内积等于余弦相似度
            embedding = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
        except Exception as e:
            error_msg = str(e).lower()
            
            # 检查是否是模型不存在的错误
            if 'model' in error_msg and ('not found' in error_msg or 'does not exist' in error_msg or 'no such model' in error_msg):
                self.logger.warning(f"Embedding模型 {self.embedding_model_name} 不存在，尝试自动下载...")
                try:
                    # 自动下载模型
                    import subprocess
                    result = subprocess.run(
                        ['ollama', 'pull', self.embedding_model_name],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    if result.returncode == 0:
                        self.logger.info(f"模型 {self.embedding_model_name} 下载成功，重试embedding...")
                        # 重试embedding
                        response = ollama.embeddings(model=self.embedding_model_name, prompt=text)
                        embedding = response['embedding']
                        
                        # 更新维度信息
                        if self.embedding_dim is None:
                            self.embedding_dim = len(embedding)
                            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
                        
                        # 归一化向量
                        embedding = np.array(embedding, dtype=np.float32)
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = embedding / norm
                        
                        return embedding
                    else:
                        self.logger.error(f"模型下载失败: {result.stderr}")
                        raise Exception(f"模型下载失败: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self.logger.error(f"模型下载超时（5分钟）")
                    raise Exception("模型下载超时")
                except Exception as download_error:
                    self.logger.error(f"模型下载失败: {download_error}")
                    raise Exception(f"模型下载失败: {download_error}")
            else:
                # 其他错误，降级到简单hash
                self.logger.warning(f"Ollama embedding失败: {e}")
                dim = self.embedding_dim or 768
                embedding = np.array([float(hashlib.md5(text.encode()).hexdigest() % 1000) for _ in range(dim)], dtype=np.float32)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding
    
    def get(self, intent: Dict[str, Any], tools: Any = None) -> Optional[Dict[str, Any]]:
        """获取缓存的计划（支持模板化匹配）"""
        conn = None
        try:
            intent_str = self._intent_to_string(intent)
            intent_hash = hashlib.md5(intent_str.encode()).hexdigest()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 方法1：精确匹配（完整计划）
            cursor.execute('''
                SELECT plan FROM cache 
                WHERE intent_hash = ? AND datetime(timestamp, '+' || ? || ' seconds') > datetime('now')
            ''', (intent_hash, self.ttl))
            
            result = cursor.fetchone()
            if result:
                # 更新最后访问时间
                cursor.execute('UPDATE cache SET last_accessed = datetime("now") WHERE intent_hash = ?', (intent_hash,))
                conn.commit()
                self.logger.info("缓存精确命中（完整计划）")
                return json.loads(result[0])
            
            # 方法2：FAISS语义匹配（基于entities模板）
            # 提取entities模板（只包含参数名称）
            entities_template = self._extract_entities_template(intent)
            entities_template_str = json.dumps(entities_template, ensure_ascii=False)
            self.logger.info(f"查询entities_template: {entities_template_str}")
            embedding = self._get_embedding(entities_template_str)
            embedding = embedding.reshape(1, -1)
            
            # 在FAISS中搜索最相似的向量（只搜索1个，因为索引和数据库已一致）
            if self.faiss_index.ntotal > 0:
                self.logger.info(f"FAISS索引中有 {self.faiss_index.ntotal} 个向量")
                distances, indices = self.faiss_index.search(embedding, k=1)
                faiss_id = int(indices[0][0])
                similarity = float(distances[0][0])  # 内积直接等于余弦相似度（因为向量已归一化）
                self.logger.info(f"FAISS搜索结果: faiss_id={faiss_id}, similarity={similarity:.2f}, threshold={self.similarity_threshold}")
                
                # 检查相似度是否超过阈值
                if similarity >= self.similarity_threshold:
                    self.logger.info(f"相似度检查通过，开始查询数据库")
                    # 检查faiss_id是否在数据库中存在（防止LRU删除导致的不一致）
                    cursor.execute('SELECT COUNT(*) FROM cache WHERE faiss_id = ?', (faiss_id,))
                    count = cursor.fetchone()[0]
                    self.logger.info(f"数据库中faiss_id={faiss_id}的记录数: {count}")
                    
                    if count > 0:
                        self.logger.info(f"开始获取完整计划")
                        # 获取完整计划和entities_template
                        cursor.execute('SELECT plan, entities_template FROM cache WHERE faiss_id = ?', (faiss_id,))
                        result = cursor.fetchone()
                        if result:
                            # 验证关键参数是否匹配（如operation）
                            cached_entities_template = json.loads(result[1])
                            cached_key_params = cached_entities_template.get("entities", {}).get("key_params", {})
                            current_entities = intent.get("entities", {})
                            
                            # 检查关键参数是否匹配
                            key_params_match = True
                            for param_name, param_value in cached_key_params.items():
                                if param_name in current_entities:
                                    if current_entities[param_name] != param_value:
                                        key_params_match = False
                                        self.logger.info(f"关键参数不匹配: {param_name} (缓存={param_value}, 当前={current_entities[param_name]})")
                                        break
                            
                            if not key_params_match:
                                self.logger.info(f"关键参数不匹配，跳过缓存")
                                return None
                            
                            self.logger.info(f"关键参数匹配成功")
                            self.logger.info(f"成功获取到缓存计划")
                            # 更新最后访问时间
                            cursor.execute('UPDATE cache SET last_accessed = datetime("now") WHERE faiss_id = ?', (faiss_id,))
                            conn.commit()
                            self.logger.info(f"缓存模板命中（相似度: {similarity:.2f}）")
                            
                            # 替换plan中的参数值
                            plan = json.loads(result[0])
                            self.logger.info(f"开始替换参数: {intent.get('entities', {})}")
                            plan = self._replace_plan_params(plan, intent)
                            self.logger.info(f"参数替换完成: {plan}")
                            
                            return plan
                        else:
                            self.logger.warning(f"数据库查询返回None，faiss_id={faiss_id}")
                    else:
                        # faiss_id在数据库中不存在（已被LRU删除），记录日志
                        self.logger.debug(f"FAISS返回的faiss_id={faiss_id}在数据库中不存在（已被LRU删除），跳过缓存")
                else:
                    self.logger.info(f"相似度未达到阈值，跳过缓存")
            else:
                self.logger.info("FAISS索引为空，跳过语义匹配")
            
            return None
        except Exception as e:
            self.logger.error(f"缓存查询失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _replace_plan_params(self, plan: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """替换plan中的参数值（基于intent中的entities）
        
        由于LLM已经根据工具的参数名生成了正确的entities，这里只需要直接替换参数值即可。
        """
        try:
            # 从intent中提取entities
            entities = intent.get("entities", {})
            if not entities:
                return plan
            
            # 深拷贝plan，避免修改原始数据
            import copy
            new_plan = copy.deepcopy(plan)
            
            # 直接替换参数值（LLM已经生成了正确的参数名）
            for step in new_plan.get("steps", []):
                args = step.get("args", {})
                
                # 遍历entities，直接替换参数值
                for param_name, param_value in entities.items():
                    if param_name in args:
                        args[param_name] = param_value
                        self.logger.debug(f"替换参数: {param_name} = {param_value}")
            
            return new_plan
        except Exception as e:
            self.logger.error(f"替换参数值失败: {e}")
            return plan
    
    def set(self, intent: Dict[str, Any], tools: Any = None, plan: Dict[str, Any] = None):
        """设置缓存（支持模板化存储）"""
        conn = None
        try:
            self.logger.info(f"开始缓存: intent={intent}, plan={plan}")
            
            intent_str = self._intent_to_string(intent)
            intent_hash = hashlib.md5(intent_str.encode()).hexdigest()
            
            self.logger.info(f"intent_str: {intent_str}")
            self.logger.info(f"intent_hash: {intent_hash}")
            
            # 提取模板
            plan_template = self._extract_template(plan)
            template_str = self._template_to_string(plan_template)
            
            # 提取entities模板（只包含参数名称）
            entities_template = self._extract_entities_template(intent)
            entities_template_str = json.dumps(entities_template, ensure_ascii=False)
            
            self.logger.info(f"template_str: {template_str}")
            self.logger.info(f"entities_template: {entities_template_str}")
            
            # 使用entities模板生成embedding向量
            embedding = self._get_embedding(entities_template_str)
            
            self.logger.info(f"embedding shape: {embedding.shape}")
            
            # 将embedding向量序列化为二进制
            embedding_blob = pickle.dumps(embedding)
            
            self.logger.info(f"embedding_blob size: {len(embedding_blob)}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute('SELECT faiss_id FROM cache WHERE intent_hash = ?', (intent_hash,))
            result = cursor.fetchone()
            
            if result:
                # 更新现有记录
                faiss_id = result[0]
                cursor.execute('''
                    UPDATE cache 
                    SET intent_str = ?, plan = ?, plan_template = ?, entities_template = ?, embedding_vector = ?, timestamp = datetime('now')
                    WHERE intent_hash = ?
                ''', (intent_str, json.dumps(plan, ensure_ascii=False), json.dumps(plan_template, ensure_ascii=False), entities_template_str, embedding_blob, intent_hash))
                self.logger.debug("更新缓存记录")
            else:
                # 添加新记录
                # 使用数据库自增ID作为faiss_id
                cursor.execute('''
                    SELECT MAX(faiss_id) FROM cache
                ''')
                max_faiss_id = cursor.fetchone()[0]
                faiss_id = (max_faiss_id + 1) if max_faiss_id is not None else 0
                
                self.logger.info(f"准备添加新记录: faiss_id={faiss_id}")
                
                cursor.execute('''
                    INSERT INTO cache (faiss_id, intent_hash, intent_str, plan, plan_template, entities_template, embedding_vector, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (faiss_id, intent_hash, intent_str, json.dumps(plan, ensure_ascii=False), json.dumps(plan_template, ensure_ascii=False), entities_template_str, embedding_blob))
                
                self.logger.info(f"数据库插入成功: faiss_id={faiss_id}")
                
                # 添加到FAISS索引（使用add_with_ids指定自定义ID）
                embedding = embedding.reshape(1, -1)
                self.faiss_index.add_with_ids(embedding, np.array([faiss_id], dtype=np.int64))
                self._save_faiss_index()
                self.logger.debug(f"添加新缓存记录，faiss_id={faiss_id}, intent: {intent_str}")
            
            conn.commit()
            self.logger.info("缓存保存成功")
        except Exception as e:
            self.logger.error(f"缓存存储失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            if conn:
                conn.close()
    
    def clear(self):
        """清空缓存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache')
            conn.commit()
            conn.close()
            
            # 清空FAISS索引
            self.faiss_index.reset()
            self._save_faiss_index()
            
            self.logger.info("缓存已清空")
        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")
    
    def cleanup_expired(self):
        """清理过期缓存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取过期的faiss_id
            cursor.execute('''
                SELECT faiss_id FROM cache 
                WHERE datetime(timestamp, '+' || ? || ' seconds') < datetime('now')
            ''', (self.ttl,))
            expired_faiss_ids = [row[0] for row in cursor.fetchall()]
            
            # 删除过期记录
            cursor.execute('''
                DELETE FROM cache 
                WHERE datetime(timestamp, '+' || ? || ' seconds') < datetime('now')
            ''', (self.ttl,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            # 如果有过期记录，重建FAISS索引
            if expired_faiss_ids:
                self._rebuild_faiss_index()
            
            self.logger.info(f"清理了 {deleted_count} 个过期缓存记录")
            return deleted_count
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    def cleanup(self):
        """混合清理策略：TTL + 大小 + LRU"""
        try:
            self.logger.info("开始执行缓存清理...")
            
            # 1. 删除过期记录（TTL）
            expired_count = self.cleanup_expired()
            
            # 2. 检查数据库大小
            db_size_mb = self._get_db_size()
            if db_size_mb > self.max_db_size_mb:
                self.logger.info(f"数据库大小 {db_size_mb}MB 超过限制 {self.max_db_size_mb}MB，执行LRU清理")
                lru_count = self._delete_lru()
                self.logger.info(f"LRU清理删除了 {lru_count} 条记录")
            
            # 3. 检查FAISS索引大小
            faiss_size_mb = self._get_faiss_size()
            if faiss_size_mb > self.max_faiss_size_mb:
                self.logger.info(f"FAISS索引大小 {faiss_size_mb}MB 超过限制 {self.max_faiss_size_mb}MB，执行LRU清理")
                lru_count = self._delete_lru()
                self.logger.info(f"LRU清理删除了 {lru_count} 条记录")
            
            # 4. 检查记录数量
            record_count = self._get_record_count()
            if record_count > self.max_records:
                self.logger.info(f"记录数量 {record_count} 超过限制 {self.max_records}，执行LRU清理")
                lru_count = self._delete_lru()
                self.logger.info(f"LRU清理删除了 {lru_count} 条记录")
            
            # 5. 检查总大小
            total_size_mb = db_size_mb + faiss_size_mb
            if total_size_mb > self.max_total_size_mb:
                self.logger.info(f"总大小 {total_size_mb}MB 超过限制 {self.max_total_size_mb}MB，执行LRU清理")
                lru_count = self._delete_lru()
                self.logger.info(f"LRU清理删除了 {lru_count} 条记录")
            
            # 6. 重建FAISS索引
            self._rebuild_faiss_index()
            
            self.logger.info("缓存清理完成")
        except Exception as e:
            self.logger.error(f"缓存清理失败: {e}")
    
    def _delete_lru(self, count: int = None):
        """删除最久未使用的记录（LRU）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 如果没有指定数量，计算需要删除的数量
            if count is None:
                current_count = self._get_record_count()
                
                # 计算需要删除的数量（删除到满足所有限制）
                if current_count > self.max_records:
                    # 记录数超限，删除到max_records
                    count = current_count - self.max_records
                else:
                    count = 0
            
            # 获取最久未使用的记录
            cursor.execute('''
                SELECT faiss_id FROM cache 
                WHERE datetime(timestamp, '+' || ? || ' seconds') > datetime('now')
                ORDER BY last_accessed ASC
                LIMIT ?
            ''', (self.ttl, count))
            
            lru_faiss_ids = [row[0] for row in cursor.fetchall()]
            
            # 删除记录
            if lru_faiss_ids:
                placeholders = ','.join(['?' for _ in lru_faiss_ids])
                cursor.execute(f'DELETE FROM cache WHERE faiss_id IN ({placeholders})', lru_faiss_ids)
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                # 从FAISS索引中删除向量（使用IndexIDMap的remove_ids）
                try:
                    self.faiss_index.remove_ids(np.array(lru_faiss_ids, dtype=np.int64))
                    self._save_faiss_index()
                    self.logger.info(f"从FAISS索引中删除了 {len(lru_faiss_ids)} 个向量")
                except Exception as e:
                    self.logger.warning(f"从FAISS索引中删除向量失败（可能已被删除）: {e}")
                
                return deleted_count
            
            conn.close()
            return 0
        except Exception as e:
            self.logger.error(f"LRU清理失败: {e}")
            return 0
    
    def _get_db_size(self) -> float:
        """获取数据库文件大小（MB）"""
        try:
            if os.path.exists(self.db_path):
                size_bytes = os.path.getsize(self.db_path)
                return round(size_bytes / (1024 * 1024), 2)
            return 0.0
        except Exception as e:
            self.logger.error(f"获取数据库大小失败: {e}")
            return 0.0
    
    def _get_faiss_size(self) -> float:
        """获取FAISS索引文件大小（MB）"""
        try:
            if os.path.exists(self.faiss_index_path):
                size_bytes = os.path.getsize(self.faiss_index_path)
                return round(size_bytes / (1024 * 1024), 2)
            return 0.0
        except Exception as e:
            self.logger.error(f"获取FAISS索引大小失败: {e}")
            return 0.0
    
    def _get_record_count(self) -> int:
        """获取记录数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM cache')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            self.logger.error(f"获取记录数量失败: {e}")
            return 0
    
    def _rebuild_faiss_index(self):
        """重建FAISS索引（从数据库读取embedding向量，只添加有效的）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有有效的缓存记录（从数据库读取embedding向量）
            cursor.execute('''
                SELECT faiss_id, embedding_vector FROM cache 
                WHERE datetime(timestamp, '+' || ? || ' seconds') > datetime('now')
                AND embedding_vector IS NOT NULL
                ORDER BY faiss_id
            ''', (self.ttl,))
            
            records = cursor.fetchall()
            conn.close()
            
            if not records:
                # 没有记录，创建空索引（使用IndexIDMap包装，支持add_with_ids）
                base_index = faiss.IndexFlatIP(self.embedding_dim)
                self.faiss_index = faiss.IndexIDMap(base_index)
                self._save_faiss_index()
                self.logger.info(f"FAISS索引重建完成，包含 0 个向量")
                return
            
            # 重建索引（只添加有效的向量，使用IndexIDMap包装，支持add_with_ids）
            base_index = faiss.IndexFlatIP(self.embedding_dim)
            self.faiss_index = faiss.IndexIDMap(base_index)
            
            for faiss_id, embedding_blob in records:
                # 从数据库反序列化embedding向量
                embedding = pickle.loads(embedding_blob)
                embedding = embedding.reshape(1, -1)
                self.faiss_index.add_with_ids(embedding, np.array([faiss_id], dtype=np.int64))
            
            self._save_faiss_index()
            self.logger.info(f"FAISS索引重建完成，包含 {len(records)} 个有效向量")
        except Exception as e:
            self.logger.error(f"重建FAISS索引失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                "cache_dir": self.cache_dir,
                "embedding_model": self.embedding_model_name,
                "similarity_threshold": self.similarity_threshold,
                "ttl": self.ttl,
                "max_total_size_mb": self.max_total_size_mb,
                "max_db_size_mb": self.max_db_size_mb,
                "max_faiss_size_mb": self.max_faiss_size_mb,
                "max_records": self.max_records,
                "cleanup_interval": self.cleanup_interval,
                "cleanup_on_startup": self.cleanup_on_startup,
                "faiss_index_size": self.faiss_index.ntotal,
                "embedding_dim": self.embedding_dim
            }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总记录数
            cursor.execute('SELECT COUNT(*) FROM cache')
            stats["total_records"] = cursor.fetchone()[0]
            
            # 有效记录数
            cursor.execute('''
                SELECT COUNT(*) FROM cache 
                WHERE datetime(timestamp, '+' || ? || ' seconds') > datetime('now')
            ''', (self.ttl,))
            stats["valid_records"] = cursor.fetchone()[0]
            
            # 过期记录数
            stats["expired_records"] = stats["total_records"] - stats["valid_records"]
            
            # 数据库文件大小
            stats["db_size_bytes"] = self._get_db_size() * 1024 * 1024
            stats["db_size_mb"] = self._get_db_size()
            
            # FAISS索引文件大小
            stats["faiss_size_bytes"] = self._get_faiss_size() * 1024 * 1024
            stats["faiss_size_mb"] = self._get_faiss_size()
            
            # 总大小
            stats["total_size_mb"] = stats["db_size_mb"] + stats["faiss_size_mb"]
            
            conn.close()
            return stats
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def _start_cleanup_thread(self):
        """启动定时清理线程"""
        try:
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            self.logger.info(f"定时清理线程已启动，间隔: {self.cleanup_interval}秒")
        except Exception as e:
            self.logger.error(f"启动清理线程失败: {e}")
    
    def _cleanup_loop(self):
        """清理循环"""
        while not self._cleanup_stop_event.is_set():
            try:
                # 等待清理间隔
                self._cleanup_stop_event.wait(self.cleanup_interval)
                
                # 检查是否需要停止
                if self._cleanup_stop_event.is_set():
                    break
                
                # 执行清理
                self.cleanup()
            except Exception as e:
                self.logger.error(f"定时清理失败: {e}")
    
    def stop_cleanup(self):
        """停止清理线程"""
        try:
            if self._cleanup_thread and self._cleanup_thread.is_alive():
                self._cleanup_stop_event.set()
                self._cleanup_thread.join(timeout=5)
                self.logger.info("清理线程已停止")
        except Exception as e:
            self.logger.error(f"停止清理线程失败: {e}")