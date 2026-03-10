"""
执行智能使用示例

展示如何在行为树中启用和使用执行智能功能。
"""

import asyncio
import json
from typing import Dict, Any

from mcp_client.behavior_tree.blackboard import BehaviorTreeBlackboard
from mcp_client.behavior_tree.nodes import NodeFactory
from mcp_client.behavior_tree.tree_executor import BehaviorTreeExecutor


async def mock_user_interaction(request) -> Dict[str, Any]:
    """模拟用户交互回调
    
    实际应用中，这应该连接到UI界面，等待用户输入。
    """
    print(f"\n{'='*50}")
    print(f"Elicitation 请求: {request.type.value}")
    print(f"节点: {request.node_name}")
    print(f"消息: {request.message}")
    
    if request.suggested_values:
        print(f"\n建议值: {request.suggested_values}")
    
    # 模拟用户输入（实际应用中从UI获取）
    print("\n[模拟用户确认]")
    
    return {
        'action': 'confirm',
        'user_input': request.suggested_values  # 接受建议值
    }


async def mock_tool_executor(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """模拟工具执行器"""
    print(f"\n执行工具: {tool_name}")
    print(f"参数: {args}")
    
    return {
        'success': True,
        'result_blackboard': f"{tool_name} 执行结果",
        'formatted_message': f"工具 {tool_name} 执行成功"
    }


def create_example_tree_with_intelligence():
    """创建带有执行智能的行为树配置"""
    
    tree_config = {
        "type": "Sequence",
        "name": "智能执行示例",
        "id": "sequenceIntelligentExample",
        "children": [
            {
                "type": "Action",
                "name": "智能推断操作",
                "id": "actionSmartInference",
                "tool": "file_operations",
                "parameters": {
                    "operation": "read",
                    # input_file 缺失，将触发执行智能
                },
                # 启用执行智能
                "intelligence_config": {
                    "enabled": True,
                    "strategy": "hybrid",  # 混合模式
                    "auto_execute_threshold": 0.85,
                    "confirm_threshold": 0.60
                }
            },
            {
                "type": "Action",
                "name": "强制确认操作",
                "id": "actionRequireConfirm",
                "tool": "email_processor",
                "parameters": {
                    "operation": "send",
                    # recipient 和 subject 缺失
                },
                "intelligence_config": {
                    "enabled": True,
                    "strategy": "elicitation"  # 强制使用Elicitation
                }
            },
            {
                "type": "Action",
                "name": "纯推断操作",
                "id": "actionPureInference",
                "tool": "weather_query",
                "parameters": {
                    # city 缺失
                },
                "intelligence_config": {
                    "enabled": True,
                    "strategy": "inference"  # 纯推断模式
                }
            }
        ]
    }
    
    return tree_config


async def main():
    """主函数"""
    print("="*60)
    print("执行智能示例程序")
    print("="*60)
    
    # 1. 初始化黑板
    blackboard = BehaviorTreeBlackboard()
    blackboard.set_user_input("请帮我处理文件和发送邮件")
    
    # 2. 创建节点工厂
    factory = NodeFactory(
        tool_executor=mock_tool_executor,
        blackboard=blackboard
    )
    
    # 3. 加载行为树配置
    tree_config = create_example_tree_with_intelligence()
    print("\n行为树配置:")
    print(json.dumps(tree_config, ensure_ascii=False, indent=2))
    
    # 4. 创建执行器
    executor = BehaviorTreeExecutor(
        tree_config=tree_config,
        node_factory=factory
    )
    
    # 5. 执行行为树
    print("\n" + "="*60)
    print("开始执行行为树...")
    print("="*60)
    
    # 注意：实际执行需要设置用户交互回调
    # 这里仅展示配置方式
    
    print("\n执行智能已配置完成！")
    print("\n关键特性:")
    print("1. 混合模式: 根据置信度自动选择执行策略")
    print("   - 置信度≥0.85: 自动执行")
    print("   - 置信度0.60-0.85: 请求确认")
    print("   - 置信度<0.60: 触发Elicitation")
    print("\n2. 策略可配置: 每个节点可独立设置策略")
    print("   - inference: 纯推断")
    print("   - elicitation: 纯Elicitation")
    print("   - hybrid: 混合模式（推荐）")
    print("   - auto: 自动选择")
    print("\n3. 学习系统: 记录用户偏好，优化未来推断")
    print("\n4. 成本控制: 监控token使用，防止预算超支")


if __name__ == "__main__":
    asyncio.run(main())
