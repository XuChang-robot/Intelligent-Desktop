import platform
import psutil
from typing import Dict, Any, Optional, Tuple
from mcp.server.fastmcp import Context
from .tool_base import ToolBase, ToolResult, OperationConfig, register_tool


@register_tool("system_info")
class SystemInfoTool(ToolBase):
    """系统信息工具
    
    获取操作系统的各种信息，包括操作系统、CPU、内存、磁盘、网络和进程信息。
    """
    
    TOOL_NAME = "system_info"
    
    OPERATION_CONFIG = {
        'all': OperationConfig(
            description='所有信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'os': OperationConfig(
            description='操作系统信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'cpu': OperationConfig(
            description='CPU信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'memory': OperationConfig(
            description='内存信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'disk': OperationConfig(
            description='磁盘信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'network': OperationConfig(
            description='网络信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        ),
        'process': OperationConfig(
            description='进程信息',
            required_params=[],
            optional_params=[],
            is_dangerous=False
        )
    }
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        """执行系统信息获取"""
        info_type = kwargs.get('operation', 'all')
        
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
        
        return (ToolResult.success(result)
            .with_message("\n".join(formatted_message))
            .build())


def register_system_info_tools(mcp):
    """注册系统信息工具到MCP服务器"""
    tool = SystemInfoTool()
    
    @mcp.tool()
    async def system_info(info_type: str = "all") -> Dict[str, Any]:
        """获取系统信息工具
        
        获取操作系统的各种信息，包括操作系统、CPU、内存、磁盘、网络和进程信息。
        
        Args:
            info_type: 信息类型（默认"all"）
                - "all": 所有信息
                - "os": 操作系统信息
                - "cpu": CPU信息
                - "memory": 内存信息
                - "disk": 磁盘信息
                - "network": 网络信息
                - "process": 进程信息
        
        Returns:
            执行结果字典
        """
        return await tool.safe_execute(operation=info_type)
    
    return system_info
