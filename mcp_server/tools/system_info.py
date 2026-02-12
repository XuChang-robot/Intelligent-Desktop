# 系统信息工具

import platform
import psutil
from typing import Dict, Any


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
            - 获取内存信息: system_info("memory")
        """
        try:
            result = {}
            
            if info_type in ["all", "os"]:
                result["os"] = {
                    "system": platform.system(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                }
            
            if info_type in ["all", "cpu"]:
                result["cpu"] = {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
                }
            
            if info_type in ["all", "memory"]:
                mem = psutil.virtual_memory()
                result["memory"] = {
                    "total": mem.total,
                    "available": mem.available,
                    "percent": mem.percent,
                    "used": mem.used
                }
            
            if info_type in ["all", "disk"]:
                disk = psutil.disk_usage('/')
                result["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            
            if info_type in ["all", "network"]:
                result["network"] = {
                    "connections": len(psutil.net_connections()),
                    "interfaces": list(psutil.net_if_addrs().keys())
                }
            
            if info_type in ["all", "process"]:
                result["process"] = {
                    "count": len(psutil.pids()),
                    "top_cpu": [p.info for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), 
                                                          key=lambda x: x.info['cpu_percent'], reverse=True)[:5]]
                }
            
            return {"success": True, "info": result}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
