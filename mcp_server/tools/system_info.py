# 系统信息工具

import platform
import psutil
from typing import Dict, Any, Optional, Tuple


# 工具创建规则：
# 1. 必须在文件最前面定义工具说明，包括工具名称、支持的操作类型、必需参数、可选参数、参数验证规则和返回格式
# 2. 必须定义操作类型配置（OPERATION_CONFIG或其他类似配置），包含各操作类型的描述、必需参数和可选参数
# 3. 必须实现validate_parameters函数，用于验证和调整参数，返回(调整后的参数字典, 配置错误信息)
# 4. 必须在工具函数开始时调用validate_parameters进行参数验证，如果存在config_error则返回包含config_error字段的错误结果
# 5. 必须统一返回字典格式结果，包含success字段和formatted_message字段
# 6. 配置错误时返回{"success": False, "config_error": "...", "formatted_message": "❌ 配置错误: ..."}
# 7. 执行失败时返回{"success": False, "error": "...", "formatted_message": "❌ 错误: ..."}
# 8. 成功时返回{"success": True, "result": "...", "formatted_message": "✅ ..."}
# 9. 必须包含operation参数，用于指定具体的操作类型
# 10. 只有当返回结果包含config_error字段时，行为树自动修复机制才会触发配置修复
# 11. formatted_message字段是系统返回给UI的信息，必须包含清晰的操作结果描述和状态标识
# 
# 原因：
# - 统一的参数验证机制确保LLM生成的配置能够被正确验证，避免参数错误导致执行失败
# - 统一的返回格式便于行为树自动修复机制识别配置错误和执行失败，只在配置错误时触发修复
# - 标准化的工具文档和配置格式便于维护和扩展，提高代码可读性
# - config_error字段明确区分配置错误和执行失败，避免误触发自动修复机制
# - operation参数是工具操作的核心标识符，确保工具能够正确执行指定的操作
# - 只有通过config_error字段，行为树系统才能准确识别LLM生成的配置错误，从而触发修复机制
# - formatted_message字段为UI提供清晰的操作结果展示，提升用户体验


# 工具说明：
# 工具名称：system_info
# 支持的信息类型（info_type）：
#   - "all": 所有信息（默认）
#   - "os": 操作系统信息
#   - "cpu": CPU信息
#   - "memory": 内存信息
#   - "disk": 磁盘信息
#   - "network": 网络信息
#   - "process": 进程信息
# 必需参数：无
# 可选参数：
#   - info_type: 信息类型（默认为"all"）
#
# 参数验证规则：
#   - info_type: 必须是支持的信息类型之一
#
# 返回格式：
#   - 成功：{"success": True, "info": {...}, "formatted_message": "..."}
#   - 配置错误：{"success": False, "config_error": "..."}
#   - 执行失败：{"success": False, "error": "...", "formatted_message": "..."}


# 信息类型配置
INFO_TYPE_CONFIG = {
    'all': {
        'description': '所有信息',
        'required_params': [],
        'optional_params': []
    },
    'os': {
        'description': '操作系统信息',
        'required_params': [],
        'optional_params': []
    },
    'cpu': {
        'description': 'CPU信息',
        'required_params': [],
        'optional_params': []
    },
    'memory': {
        'description': '内存信息',
        'required_params': [],
        'optional_params': []
    },
    'disk': {
        'description': '磁盘信息',
        'required_params': [],
        'optional_params': []
    },
    'network': {
        'description': '网络信息',
        'required_params': [],
        'optional_params': []
    },
    'process': {
        'description': '进程信息',
        'required_params': [],
        'optional_params': []
    }
}


def validate_parameters(info_type: str = "all") -> Tuple[Dict[str, Any], Optional[str]]:
    """验证并调整参数
    
    Args:
        info_type: 信息类型
    
    Returns:
        (调整后的参数字典, 配置错误信息)
    """
    params = {
        'info_type': info_type
    }
    
    config_error = None
    
    # 验证info_type参数
    if info_type and info_type not in INFO_TYPE_CONFIG:
        config_error = f"不支持的信息类型: {info_type}，支持的类型: {', '.join(INFO_TYPE_CONFIG.keys())}"
    
    return params, config_error


def register_system_info_tools(mcp):
    """注册系统信息工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
    @mcp.tool()
    async def system_info(info_type: str = "all") -> Dict[str, Any]:
        """获取系统信息工具
        
        获取操作系统的各种信息，包括操作系统、CPU、内存、磁盘、网络和进程信息。
        
        Args:
            info_type: 信息类型，可选值：
                - "all": 所有信息（默认）
                - "os": 操作系统信息
                - "cpu": CPU信息
                - "memory": 内存信息
                - "disk": 磁盘信息
                - "network": 网络信息
                - "process": 进程信息
        
        Returns:
            {
                "success": True/False,
                "info": 系统信息字典，包含请求类型的信息
            }
        
        Examples:
            - 获取所有信息: system_info()
            - 获取CPU信息: system_info("cpu")
        """
        try:
            # 参数验证
            params, config_error = validate_parameters(info_type)
            
            # 如果存在配置错误，返回错误
            if config_error:
                return {
                    "success": False,
                    "config_error": config_error
                }
            
            info_type = params['info_type']
            
            result = {}
            formatted_message = []
            
            if info_type in ["all", "os"]:
                os_info = {
                    "system": platform.system(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                }
                result["os"] = os_info
                formatted_message.append("💻 操作系统信息:")
                formatted_message.append(f"  系统: {os_info['system']}")
                formatted_message.append(f"  版本: {os_info['version']}")
                formatted_message.append(f"  架构: {os_info['machine']}")
                formatted_message.append(f"  处理器: {os_info['processor']}")
            
            if info_type in ["all", "cpu"]:
                cpu_info = {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
                }
                result["cpu"] = cpu_info
                formatted_message.append("\n⚡ CPU信息:")
                formatted_message.append(f"  使用率: {cpu_info['percent']}%")
                formatted_message.append(f"  核心数: {cpu_info['count']}")
                if cpu_info['freq']:
                    formatted_message.append(f"  频率: {cpu_info['freq'].get('current', 0):.1f}MHz")
            
            if info_type in ["all", "memory"]:
                mem = psutil.virtual_memory()
                memory_info = {
                    "total": mem.total,
                    "available": mem.available,
                    "percent": mem.percent,
                    "used": mem.used
                }
                result["memory"] = memory_info
                formatted_message.append("\n🗃️ 内存信息:")
                formatted_message.append(f"  总内存: {mem.total / (1024**3):.2f}GB")
                formatted_message.append(f"  已使用: {mem.used / (1024**3):.2f}GB ({mem.percent}%)")
                formatted_message.append(f"  可用: {mem.available / (1024**3):.2f}GB")
            
            if info_type in ["all", "disk"]:
                disk = psutil.disk_usage('/')
                disk_info = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
                result["disk"] = disk_info
                formatted_message.append("\n💽 磁盘信息:")
                formatted_message.append(f"  总空间: {disk.total / (1024**3):.2f}GB")
                formatted_message.append(f"  已使用: {disk.used / (1024**3):.2f}GB ({disk.percent}%)")
                formatted_message.append(f"  可用: {disk.free / (1024**3):.2f}GB")
            
            if info_type in ["all", "network"]:
                network_info = {
                    "connections": len(psutil.net_connections()),
                    "interfaces": list(psutil.net_if_addrs().keys())
                }
                result["network"] = network_info
                formatted_message.append("\n🌐 网络信息:")
                formatted_message.append(f"  连接数: {network_info['connections']}")
                formatted_message.append(f"  网络接口: {', '.join(network_info['interfaces'])}")
            
            if info_type in ["all", "process"]:
                process_info = {
                    "count": len(psutil.pids()),
                    "top_cpu": [p.info for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), 
                                                          key=lambda x: x.info['cpu_percent'], reverse=True)[:5]]
                }
                result["process"] = process_info
                formatted_message.append("\n📊 进程信息:")
                formatted_message.append(f"  进程总数: {process_info['count']}")
                if process_info['top_cpu']:
                    formatted_message.append("  CPU使用率最高的进程:")
                    for p in process_info['top_cpu']:
                        if p.get('cpu_percent', 0) > 0:
                            formatted_message.append(f"    - {p['name']} (PID: {p['pid']}): {p['cpu_percent']:.1f}%")
            
            return {
                "success": True, 
                "info": result,
                "formatted_message": "\n".join(formatted_message)
            }
        
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "formatted_message": f"❌ 错误: {str(e)}"
            }
