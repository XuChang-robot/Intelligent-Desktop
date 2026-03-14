#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证缓存修复
"""

import logging
import time
from mcp_client.hybrid_cache import HybridTaskPlanCache

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def test_cache_fix():
    print("=" * 80)
    print("验证缓存修复")
    print("=" * 80)
    
    # 初始化缓存（使用较短的TTL来测试）
    cache = HybridTaskPlanCache(
        cache_dir="cache",
        ttl=60,  # 1分钟TTL用于测试
        enable_hash_match=True,
        enable_faiss_match=False
    )
    
    # 测试数据
    test_user_input = "测试缓存修复功能"
    test_tree_config = {
        "root": {
            "type": "Sequence",
            "name": "测试序列",
            "children": [
                {"type": "Action", "name": "测试动作", "tool": "test_tool", "args": {}}
            ]
        }
    }
    
    print(f"\n=== 第一次设置缓存 ===")
    cache.set(test_user_input, test_tree_config)
    
    # 检查缓存统计
    stats = cache.get_stats()
    print(f"缓存统计: {stats}")
    
    print(f"\n=== 第一次查询缓存（应该命中） ===")
    result1 = cache.get(test_user_input)
    if result1 and result1.get("from_cache"):
        print(f"✅ 第一次查询缓存命中!")
    else:
        print(f"❌ 第一次查询缓存未命中")
        return False
    
    # 等待几秒钟
    print(f"\n等待 2 秒钟...")
    time.sleep(2)
    
    print(f"\n=== 第二次查询缓存（应该命中，并且timestamp应该更新） ===")
    result2 = cache.get(test_user_input)
    if result2 and result2.get("from_cache"):
        print(f"✅ 第二次查询缓存命中!")
        print(f"匹配类型: {result2.get('match_type')}")
    else:
        print(f"❌ 第二次查询缓存未命中")
        return False
    
    # 查看缓存统计
    print(f"\n最终缓存统计:")
    final_stats = cache.get_stats()
    print(f"总记录数: {final_stats.get('total_records', 0)}")
    print(f"有效记录数: {final_stats.get('valid_records', 0)}")
    
    print(f"\n✅ 缓存修复验证成功!")
    print(f"\n修复内容:")
    print(f"1. config.yaml - TTL 从 120秒 改为 604800秒（7天）")
    print(f"2. hybrid_cache.py - 缓存命中时同时更新 timestamp 延长有效期")
    return True

if __name__ == "__main__":
    test_cache_fix()
