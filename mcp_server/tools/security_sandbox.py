# 安全沙箱模块
# 用于限制文件系统操作的安全边界

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional


class SecurityPolicy:
    """安全策略配置"""
    
    def __init__(self):
        # 允许的根目录（沙箱边界）
        self.allowed_root_dirs: List[str] = [
            str(Path.home() / "Desktop"),
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
            str(Path.home() / "Pictures"),
            str(Path.home() / "Music"),
            str(Path.home() / "Videos"),
            os.getcwd()
        ]
        
        # 禁止的路径模式（正则表达式）
        self.blocked_paths: List[str] = [
            r'^C:\\Windows\\',
            r'^C:\\Program Files\\',
            r'^C:\\Program Files \(x86\)\\',
            r'^C:\\ProgramData\\',
            r'^C:\\Users\\.*\\AppData\\',
            r'^C:\\Users\\.*\\Local\\',
            r'^C:\\Users\\.*\\LocalLow\\',
            r'^C:\\Users\\.*\\Roaming\\',
            r'^C:\\System32\\',
            r'^C:\\SysWOW64\\',
            r'^C:\\Boot\\',
            r'^C:\\Recovery\\',
        ]
        
        # 允许的操作类型
        self.allowed_operations: List[str] = [
            'create', 'read', 'write', 'list', 
            'copy', 'check_permission', 'search', 'read_write'
        ]
        
        # 需要确认的危险操作
        self.dangerous_operations: List[str] = [
            'delete', 'move'
        ]
        
        # 路径安全检查
        self.allow_symlinks: bool = False
        self.allow_hardlinks: bool = False


class SecurityChecker:
    """安全检查器"""
    
    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
    
    def _normalize_path(self, path: str) -> str:
        """规范化路径"""
        # 展开路径中的~符号
        path = os.path.expanduser(path)
        # 规范化路径
        path = os.path.normpath(path)
        # 获取绝对路径
        path = os.path.abspath(path)
        return path
    
    def _is_path_in_allowed_root(self, path: str) -> bool:
        """检查路径是否在允许的根目录内"""
        # 检查默认允许的目录
        for root_dir in self.policy.allowed_root_dirs:
            root_dir = self._normalize_path(root_dir)
            if path.startswith(root_dir):
                return True
        
        # 允许非系统盘符（除了C盘）的任何路径
        drive_letter = os.path.splitdrive(path)[0]
        if drive_letter and drive_letter.upper() != 'C:':
            return True
        
        return False
    
    def _is_path_blocked(self, path: str) -> bool:
        """检查路径是否被禁止"""
        for blocked_pattern in self.policy.blocked_paths:
            if re.match(blocked_pattern, path):
                return True
        return False
    
    def _is_path_traversal(self, original_path: str, normalized_path: str) -> bool:
        """检查是否存在路径遍历攻击"""
        # 检查是否包含 ../ 或类似的路径遍历
        if '..' in original_path:
            # 比较原始路径和规范化路径的深度
            original_parts = original_path.split(os.sep)
            normalized_parts = normalized_path.split(os.sep)
            # 如果规范化后的路径比原始路径短，可能存在路径遍历
            if len(normalized_parts) < len(original_parts):
                return True
        return False
    
    def _check_symlink(self, path: str) -> bool:
        """检查符号链接安全"""
        if not self.policy.allow_symlinks:
            if os.path.islink(path):
                return False
        return True
    
    def check_path(self, path: str) -> Tuple[bool, str]:
        """检查路径是否安全
        
        Args:
            path: 要检查的路径
            
        Returns:
            (是否安全, 错误信息)
        """
        try:
            # 规范化路径
            normalized_path = self._normalize_path(path)
            
            # 检查路径遍历攻击
            if self._is_path_traversal(path, normalized_path):
                return False, f"路径包含遍历攻击: {path}"
            
            # 检查是否在允许的根目录内
            if not self._is_path_in_allowed_root(normalized_path):
                return False, f"路径超出允许的沙箱范围: {normalized_path}"
            
            # 检查是否被禁止
            if self._is_path_blocked(normalized_path):
                return False, f"路径被禁止访问: {normalized_path}"
            
            # 检查符号链接
            if not self._check_symlink(normalized_path):
                return False, f"不允许访问符号链接: {normalized_path}"
            
            return True, ""
        except Exception as e:
            return False, f"路径检查失败: {str(e)}"
    
    def check_operation(self, operation: str) -> Tuple[bool, str]:
        """检查操作是否允许
        
        Args:
            operation: 操作类型
            
        Returns:
            (是否允许, 错误信息)
        """
        # 检查操作类型是否允许
        if operation not in self.policy.allowed_operations:
            if operation not in self.policy.dangerous_operations:
                return False, f"不允许的操作类型: {operation}"
        
        return True, ""
    
    def is_dangerous_operation(self, operation: str) -> bool:
        """检查是否为危险操作
        
        Args:
            operation: 操作类型
            
        Returns:
            是否为危险操作
        """
        return operation in self.policy.dangerous_operations


def create_default_security_checker() -> SecurityChecker:
    """创建默认的安全检查器"""
    policy = SecurityPolicy()
    return SecurityChecker(policy)


def create_strict_security_checker() -> SecurityChecker:
    """创建严格的安全检查器"""
    policy = SecurityPolicy()
    policy.allowed_root_dirs = [str(Path.home() / "Desktop")]
    policy.blocked_paths = [r'^C:\\']
    policy.allowed_operations = ['create', 'read', 'write', 'list']
    policy.dangerous_operations = ['delete', 'move', 'copy']
    policy.max_file_size = 5 * 1024 * 1024  # 5MB
    policy.max_operations_per_minute = 30
    return SecurityChecker(policy)


def create_relaxed_security_checker() -> SecurityChecker:
    """创建宽松的安全检查器"""
    policy = SecurityPolicy()
    policy.allowed_root_dirs = [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Documents"),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Pictures"),
        str(Path.home() / "Music"),
        str(Path.home() / "Videos")
    ]
    policy.blocked_paths = [
        r'^C:\\Windows\\',
        r'^C:\\Program Files\\',
        r'^C:\\Program Files \(x86\)\\',
        r'^C:\\System32\\',
        r'^C:\\SysWOW64\\'
    ]
    policy.allowed_operations = ['create', 'read', 'write', 'list', 'copy', 'check_permission', 'search']
    policy.dangerous_operations = ['delete', 'move']
    policy.max_file_size = 20 * 1024 * 1024  # 20MB
    policy.max_operations_per_minute = 120
    return SecurityChecker(policy)