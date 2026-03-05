#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行为树自动修复模块

当行为树执行出错时，自动分析错误并通过LLM修复配置
"""

import json
import logging
from typing import Dict, Any, Optional
from mcp_client.llm import BEHAVIOR_TREE_CONFIG_PRINCIPLES

class BehaviorTreeRepair:
    """行为树自动修复模块"""
    
    def __init__(self, llm, max_repair_attempts: int = 3, tools=None):
        """
        初始化行为树修复模块
        
        Args:
            llm: LLM实例，用于生成修复方案
            max_repair_attempts: 最大修复尝试次数
            tools: 工具列表，用于生成修复提示
        """
        self.llm = llm
        self.max_repair_attempts = max_repair_attempts
        self.repair_count = 0
        self.tools = tools
        self.logger = logging.getLogger(__name__)
    
    async def repair_behavior_tree(self, original_config: Dict[str, Any], error_info: str, blackboard_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """修复行为树配置
        
        Args:
            original_config: 原始行为树配置
            error_info: 错误信息
            blackboard_data: 黑板数据，包含各节点的执行结果
            
        Returns:
            修复后的行为树配置，如果修复失败则返回None
        """
        if self.repair_count >= self.max_repair_attempts:
            self.logger.warning(f"已达到最大修复尝试次数: {self.max_repair_attempts}")
            return None
        
        self.logger.info(f"开始修复行为树，错误信息: {error_info}")
        
        # 构建修复提示
        prompt = self._build_repair_prompt(original_config, error_info, blackboard_data)
        
        # 调用LLM生成修复方案
        try:
            self.logger.info("调用LLM生成修复方案...")
            result = await self.llm.generate(prompt)
            self.logger.info("LLM修复方案生成完成")
            
            # 获取生成的响应文本
            response_text = result.get("response", "")
            if not response_text:
                self.logger.error("LLM未生成任何响应")
                return None
            
            # 解析修复后的配置
            repaired_config = self._parse_repaired_config(response_text)
            if repaired_config:
                self.repair_count += 1
                self.logger.info(f"行为树修复成功，当前尝试次数: {self.repair_count}")
                return repaired_config
            else:
                self.logger.error("无法解析LLM生成的修复方案")
                return None
        except Exception as e:
            self.logger.error(f"修复行为树时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_repair_prompt(self, config: Dict[str, Any], error: str, blackboard_data: Optional[Dict[str, Any]] = None) -> str:
        """
        构建修复提示
        
        Args:
            config: 原始行为树配置
            error: 错误信息
            blackboard_data: 黑板数据，包含各节点的执行结果
            
        Returns:
            修复提示字符串
        """
        import json
        
        prompt = f"""
你是一个行为树修复专家，需要修复以下行为树配置中的错误。

## 待修复的行为树配置
{json.dumps(config, ensure_ascii=False, indent=2)}

## 待修复行为树配置存在的错误信息
{error}

"""
        
        # 添加黑板数据
        if blackboard_data:
            prompt += f"""
## 待修复行为树配置的黑板数据（各节点执行结果）
{json.dumps(blackboard_data, ensure_ascii=False, indent=2)}

"""
        
        # 添加工具信息
        tools_info = self._format_tools_for_prompt()
        
        if tools_info:
            prompt += f"""
根据待修复行为树配置的错误信息，严格按照以下行为树配置原则和工具信息修复行为树配置中的错误：

## 行为树配置原则：
{BEHAVIOR_TREE_CONFIG_PRINCIPLES}

## 工具信息：
{tools_info}

"""
        
        prompt += f"""
*** 修复要求 ***
1. 分析错误信息和黑板数据，找出配置中的具体问题，包括不支持的操作类型、缺失参数、参数格式错误等。
2. 确保所有工具调用都使用正确的参数格式
3. 修复行为树中的键值错误
6. 只返回修复后的完整行为树配置，不要包含其他解释性文字
7. 确保返回的是有效的JSON格式
8. 必须保持原始行为树配置的JSON结构，不要添加或删除任何树节点
9. 严格按上述提供的工具信息和行为树配置原则去修复行为树配置中的错误

"""
        return prompt
    
    def _format_tools_for_prompt(self) -> str:
        """
        将工具列表格式化为修复提示中使用的文本格式
        
        Returns:
            格式化后的工具描述文本
        """
        if not self.tools:
            return ""
        
        # 格式化工具信息（包含参数）
        tools_info = ""
        if self.tools:
            tools_info = "\n\n可用工具列表：\n"
            for tool in self.tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else ""
                tools_info += f"- {tool_name}: {tool_desc}\n"
                
                # 添加工具参数信息
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    tools_info += f"  参数：\n"
                    properties = tool.inputSchema.get('properties', {})
                    required = tool.inputSchema.get('required', [])
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get('description', '')
                        param_type = param_info.get('type', 'unknown')
                        is_required = param_name in required
                        required_mark = " (必需)" if is_required else " (可选)"
                        tools_info += f"    - {param_name}: {param_type}{required_mark}"
                        if param_desc:
                            tools_info += f" - {param_desc}"
                        tools_info += "\n"
                    tools_info += "\n"
        return tools_info
    
    def _parse_repaired_config(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析修复后的配置
        
        Args:
            response: LLM的响应
            
        Returns:
            解析后的配置字典，或None如果解析失败
        """
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
                config = json.loads(json_str)
                return config
            else:
                # 尝试直接解析整个响应
                config = json.loads(response)
                return config
        except json.JSONDecodeError as e:
            self.logger.error(f"解析修复后的配置失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"解析修复配置时发生错误: {e}")
            return None
    
    def reset_repair_count(self):
        """
        重置修复计数
        """
        self.repair_count = 0
    
    def get_repair_count(self) -> int:
        """
        获取当前修复计数
        
        Returns:
            当前修复尝试次数
        """
        return self.repair_count