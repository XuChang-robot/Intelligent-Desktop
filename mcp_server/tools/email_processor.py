import os
import smtplib
import imaplib
import email
import socket
import re
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional, List, Tuple
from mcp.server.fastmcp import Context
from .tool_base import ToolBase, ToolResult, OperationConfig, register_tool
from .file_operations import FileOperationsTool

from user_config.config import get_config


class EmailOperationEnum(str, Enum):
    SEND = "send"
    RECEIVE = "receive"


@register_tool("email_processor")
class EmailProcessorTool(ToolBase):
    """邮件处理工具
    
    支持发送邮件（含附件）和接收邮件功能。
    """
    
    TOOL_NAME = "email_processor"
    
    OPERATION_CONFIG = {
        'send': OperationConfig(
            description='发送邮件',
            required_params=['recipient', 'subject', 'body'],
            optional_params=['attachments', 'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password'],
            is_dangerous=False
        ),
        'receive': OperationConfig(
            description='接收邮件',
            required_params=['recipient'],
            optional_params=['imap_server', 'imap_port', 'smtp_username', 'smtp_password'],
            is_dangerous=False
        )
    }
    
    def _validate_email(self, email_address: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email_address))
    
    def _get_email_provider(self, smtp_server: str) -> str:
        if "163.com" in smtp_server:
            return "163"
        elif "qq.com" in smtp_server:
            return "qq"
        return "unknown"
    
    def _get_smtp_config(self, smtp_server: Optional[str], smtp_port: Optional[int], 
                          smtp_username: Optional[str], smtp_password: Optional[str]) -> Tuple[str, int, str, str]:
        smtp_server = smtp_server or os.getenv('SMTP_SERVER', '') or get_config("email.smtp.server", "smtp.example.com")
        
        email_provider = self._get_email_provider(smtp_server)
        
        try:
            smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '')) if os.getenv('SMTP_PORT', '') else None
        except ValueError:
            smtp_port = None
        smtp_port = smtp_port or get_config("email.smtp.port", 465)
        
        if email_provider == "163":
            smtp_username = smtp_username or os.getenv('SMTP_163_USERNAME', '') or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
            smtp_password = smtp_password or os.getenv('SMTP_163_PASSWORD', '') or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
        elif email_provider == "qq":
            smtp_username = smtp_username or os.getenv('SMTP_QQ_USERNAME', '') or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
            smtp_password = smtp_password or os.getenv('SMTP_QQ_PASSWORD', '') or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
        else:
            smtp_username = smtp_username or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
            smtp_password = smtp_password or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
        
        return smtp_server, smtp_port, smtp_username, smtp_password
    
    def _get_imap_config(self, imap_server: Optional[str], imap_port: Optional[int]) -> Tuple[str, int]:
        imap_server = imap_server or os.getenv('IMAP_SERVER', '') or get_config("email.imap.server", "")
        
        try:
            imap_port = imap_port or int(os.getenv('IMAP_PORT', '')) if os.getenv('IMAP_PORT', '') else None
        except ValueError:
            imap_port = None
        imap_port = imap_port or get_config("email.imap.port", 993)
        
        return imap_server, imap_port
    
    def validate_parameters(self, operation: str, **kwargs) -> Tuple[Dict[str, Any], Optional[str]]:
        params, config_error = super().validate_parameters(operation, **kwargs)
        if config_error:
            return params, config_error
        
        recipient = kwargs.get('recipient')
        if not recipient:
            return params, "recipient参数不能为空"
        
        if not self._validate_email(recipient):
            return params, f"邮箱地址格式不正确: {recipient}"
        
        if operation == 'send':
            subject = kwargs.get('subject')
            body = kwargs.get('body')
            if not subject:
                return params, "send操作需要subject参数"
            if not body:
                return params, "send操作需要body参数"
        
        return params, None
    
    async def execute(self, ctx: Optional[Context] = None, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        recipient = kwargs.get('recipient')
        subject = kwargs.get('subject')
        body = kwargs.get('body')
        attachments = kwargs.get('attachments')
        smtp_server = kwargs.get('smtp_server')
        smtp_port = kwargs.get('smtp_port')
        smtp_username = kwargs.get('smtp_username')
        smtp_password = kwargs.get('smtp_password')
        imap_server = kwargs.get('imap_server')
        imap_port = kwargs.get('imap_port')
        
        smtp_server, smtp_port, smtp_username, smtp_password = self._get_smtp_config(
            smtp_server, smtp_port, smtp_username, smtp_password
        )
        
        if operation == 'send':
            if not await self._confirm_with_permission(
                ctx,
                f"确认发送邮件\n📧 收件人: {recipient}\n📝 主题: {subject or '无'}\n📎 附件: {f'（含{len(attachments.split(';')) if attachments else 0}个附件）' if attachments else ''}\n🌐 服务器: {smtp_server}:{smtp_port}",
                **kwargs
            ):
                return ToolResult.error("用户取消发送邮件").build()
            
            return self._send_email(
                recipient, subject, body, attachments,
                smtp_server, smtp_port, smtp_username, smtp_password
            )
        elif operation == 'receive':
            imap_server, imap_port = self._get_imap_config(imap_server, imap_port)
            return self._receive_email(
                recipient, imap_server, imap_port, smtp_username, smtp_password
            )
        else:
            return ToolResult.error(f"不支持的操作: {operation}").build()
    
    def _send_email(self, recipient: str, subject: str, body: str, attachments: Optional[str],
                    smtp_server: str, smtp_port: int, smtp_username: str, smtp_password: str) -> Dict[str, Any]:
        if not smtp_username:
            return ToolResult.error("缺少SMTP用户名，请在配置文件中设置或直接提供").build()
        if not smtp_password:
            return ToolResult.error("缺少SMTP密码，请在配置文件中设置或直接提供").build()
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = recipient
            msg['Subject'] = subject or ""
            
            msg.attach(MIMEText(body or "", 'plain', 'utf-8'))
            
            attachment_count = 0
            if attachments:
                attachment_paths = [p.strip() for p in attachments.split(";" if ";" in attachments else ",")]
                for attachment_path in attachment_paths:
                    if attachment_path:
                        processed_path = FileOperationsTool.process_path_static(attachment_path)
                        
                        if not os.path.exists(processed_path):
                            return (ToolResult.error(f"附件文件不存在: {processed_path}")
                                .with_message(f"❌ 错误: 附件文件不存在\n📄 文件: {os.path.basename(processed_path)}\n📍 路径: {processed_path}")
                                .build())
                        
                        attachment_count += 1
                        with open(processed_path, 'rb') as f:
                            part = MIMEApplication(f.read())
                            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(processed_path))
                            msg.attach(part)
            
            email_provider = self._get_email_provider(smtp_server)
            
            try:
                if email_provider == "163":
                    server = smtplib.SMTP_SSL(smtp_server, 465, timeout=30)
                else:
                    if smtp_port == 465:
                        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                    else:
                        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                        server.starttls()
                
                server.set_debuglevel(2)
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, recipient, msg.as_string())
                server.quit()
            finally:
                try:
                    server.quit()
                except:
                    pass
            
            return (ToolResult.success(f"邮件发送成功，收件人: {recipient}")
                .with_message(f"✅ 邮件发送成功\n📧 收件人: {recipient}\n📤 发件人: {smtp_username}\n📝 主题: {subject or '无'}\n📎 附件数: {attachment_count}\n🌐 服务器: {smtp_server}:{smtp_port}")
                .build())
        
        except socket.gaierror as e:
            return (ToolResult.error(f"DNS 解析错误: {str(e)}")
                .with_message(f"❌ DNS 解析错误\n🌐 服务器: {smtp_server}\n💬 错误: {str(e)}")
                .build())
        except socket.timeout as e:
            return (ToolResult.error(f"连接超时错误: {str(e)}")
                .with_message(f"❌ 连接超时错误\n🌐 服务器: {smtp_server}:{smtp_port}\n💬 错误: {str(e)}")
                .build())
        except smtplib.SMTPAuthenticationError:
            return (ToolResult.error("SMTP 认证失败")
                .with_message("❌ SMTP 认证失败\n💡 请检查用户名和密码是否正确")
                .build())
        except smtplib.SMTPConnectError as e:
            return (ToolResult.error(f"SMTP 连接失败: {str(e)}")
                .with_message(f"❌ SMTP 连接失败\n🌐 服务器: {smtp_server}:{smtp_port}\n💬 错误: {str(e)}")
                .build())
        except Exception as e:
            return ToolResult.error(f"发送邮件失败: {str(e)}").build()
    
    def _receive_email(self, recipient: str, imap_server: str, imap_port: int,
                       smtp_username: str, smtp_password: str) -> Dict[str, Any]:
        if not smtp_username:
            return ToolResult.error("缺少邮箱用户名，请在配置文件中设置或直接提供").build()
        if not smtp_password:
            return ToolResult.error("缺少邮箱密码，请在配置文件中设置或直接提供").build()
        
        if not imap_server or not imap_port:
            return ToolResult.error("接收邮件需要提供IMAP服务器地址和端口").build()
        
        try:
            with imaplib.IMAP4_SSL(imap_server, imap_port) as server:
                server.login(smtp_username, smtp_password)
                server.select('INBOX')
                
                status, messages = server.search(None, f'FROM "{recipient}"')
                
                if status != 'OK':
                    return ToolResult.error("搜索邮件失败").build()
                
                email_ids = messages[0].split()
                email_ids = email_ids[-10:]
                
                received_emails = []
                for email_id in email_ids:
                    status, msg_data = server.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            email_info = {
                                "from": msg.get('From'),
                                "to": msg.get('To'),
                                "subject": msg.get('Subject'),
                                "date": msg.get('Date'),
                                "body": ""
                            }
                            
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                                        email_info["body"] = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                        break
                            else:
                                if msg.get_content_type() == 'text/plain':
                                    email_info["body"] = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                            
                            received_emails.append(email_info)
                
                formatted_msg = f"✅ 成功接收 {len(received_emails)} 封邮件\n📧 发件人: {recipient}\n📥 收件箱: {smtp_username}"
                if received_emails:
                    formatted_msg += "\n\n📋 邮件列表:"
                    for i, email_info in enumerate(received_emails[:3], 1):
                        formatted_msg += f"\n\n{i}. 主题: {email_info['subject'] or '无'}"
                        formatted_msg += f"\n   日期: {email_info['date'] or '未知'}"
                        formatted_msg += f"\n   发件人: {email_info['from'] or '未知'}"
                        if len(email_info['body']) > 100:
                            formatted_msg += f"\n   正文: {email_info['body'][:100]}..."
                        else:
                            formatted_msg += f"\n   正文: {email_info['body'] or '无'}"
                    if len(received_emails) > 3:
                        formatted_msg += f"\n\n... 还有 {len(received_emails) - 3} 封邮件未显示"
                
                return (ToolResult.success(f"成功接收 {len(received_emails)} 封邮件")
                    .with_extra("emails", received_emails)
                    .with_message(formatted_msg)
                    .build())
        
        except Exception as e:
            return ToolResult.error(f"接收邮件失败: {str(e)}").build()


def register_email_processor_tools(mcp, security_checker=None, output_callback=None):
    """注册邮件处理工具到MCP服务器"""
    tool = EmailProcessorTool()
    
    @mcp.tool()
    async def email_processor(
        operation: EmailOperationEnum,
        recipient: str,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        attachments: Optional[str] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        execution_mode: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """邮件处理工具
        
        支持发送邮件（含附件）和接收邮件功能。
        
        Args:
            operation: 操作类型
                - "send": 发送邮件
                - "receive": 接收邮件
            recipient: 收件人邮箱地址（发送）或发件人邮箱地址（接收）
        
        send 操作参数:
            subject: 邮件主题（必需）
            body: 邮件正文（必需）
            attachments: 附件路径（多个用分号分隔）
        
        可选参数:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP服务器端口
            smtp_username: SMTP用户名
            smtp_password: SMTP密码
            imap_server: IMAP服务器地址
            imap_port: IMAP服务器端口
        
        Returns:
            执行结果字典
        """
        return await tool.safe_execute(
            operation=operation,
            recipient=recipient,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            subject=subject,
            body=body,
            attachments=attachments,
            imap_server=imap_server,
            imap_port=imap_port,
            execution_mode=execution_mode,
            ctx=ctx
        )
    
    return email_processor
