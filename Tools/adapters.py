# -*- coding: utf-8 -*-
"""
适配器模块 - 将原有 API 调用转换为 botpy API
"""

import asyncio
import base64
import io
from typing import Optional, Dict, Any, List, Union


class MessageAdapter:
    """消息格式适配器"""
    
    @staticmethod
    def text_to_botpy(content: str) -> Dict[str, Any]:
        """
        将文本转换为 botpy 消息格式
        
        Args:
            content: 文本内容
            
        Returns:
            botpy 消息参数
        """
        return {"content": content}
    
    @staticmethod
    def image_to_botpy(image_data: str) -> Optional[Dict[str, Any]]:
        """
        将图片数据转换为 botpy 格式
        
        Args:
            image_data: base64 编码的图片或 URL
            
        Returns:
            botpy 图片参数
        """
        if image_data.startswith("base64://"):
            # base64 图片需要上传
            return {"image": image_data}
        elif image_data.startswith("http"):
            # URL 图片
            return {"image": image_data}
        return None
    
    @staticmethod
    def markdown_to_botpy(content: str, params: Dict = None) -> Dict[str, Any]:
        """
        将内容转换为 Markdown 消息格式
        
        Args:
            content: Markdown 内容
            params: 模板参数
            
        Returns:
            Markdown 消息参数
        """
        markdown = {"custom_template_id": content}
        if params:
            markdown["params"] = params
        return {"markdown": markdown}
    
    @staticmethod
    def ark_to_botpy(template_id: str, kv: List[Dict] = None) -> Dict[str, Any]:
        """
        将内容转换为 Ark 消息格式
        
        Args:
            template_id: 模板 ID
            kv: 键值对列表
            
        Returns:
            Ark 消息参数
        """
        ark = {"template_id": template_id}
        if kv:
            ark["kv"] = kv
        return {"ark": ark}


class ActionAdapter:
    """动作适配器 - 将原有动作转换为 botpy API"""
    
    def __init__(self, client):
        """
        初始化动作适配器
        
        Args:
            client: botpy.Client 实例
        """
        self.client = client
        self.msg_adapter = MessageAdapter()
    
    async def send_text(self, channel_id: str, content: str, 
                         msg_id: str = None) -> Any:
        """
        发送文本消息
        
        Args:
            channel_id: 频道 ID
            content: 文本内容
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "content": content}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def send_image(self, channel_id: str, image: str,
                          msg_id: str = None) -> Any:
        """
        发送图片消息
        
        Args:
            channel_id: 频道 ID
            image: 图片 URL 或 base64
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "image": image}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def send_markdown(self, channel_id: str, markdown: Dict,
                             msg_id: str = None) -> Any:
        """
        发送 Markdown 消息
        
        Args:
            channel_id: 频道 ID
            markdown: Markdown 配置
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "markdown": markdown}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def send_ark(self, channel_id: str, ark: Dict,
                        msg_id: str = None) -> Any:
        """
        发送 Ark 消息
        
        Args:
            channel_id: 频道 ID
            ark: Ark 配置
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "ark": ark}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def send_embed(self, channel_id: str, embed: Dict,
                          msg_id: str = None) -> Any:
        """
        发送 Embed 消息
        
        Args:
            channel_id: 频道 ID
            embed: Embed 配置
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "embed": embed}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def send_keyboard(self, channel_id: str, keyboard: Dict,
                             msg_id: str = None) -> Any:
        """
        发送带键盘的消息
        
        Args:
            channel_id: 频道 ID
            keyboard: 键盘配置
            msg_id: 引用消息 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "keyboard": keyboard}
        if msg_id:
            params["msg_id"] = msg_id
        return await self.client.api.post_message(**params)
    
    async def recall_message(self, channel_id: str, message_id: str) -> Any:
        """
        撤回消息
        
        Args:
            channel_id: 频道 ID
            message_id: 消息 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.recall_message(
            channel_id=channel_id,
            message_id=message_id
        )
    
    async def mute_member(self, channel_id: str, user_id: str,
                           mute_seconds: str = "60") -> Any:
        """
        禁言成员
        
        Args:
            channel_id: 频道 ID
            user_id: 用户 ID
            mute_seconds: 禁言时长（秒）
            
        Returns:
            API 响应
        """
        return await self.client.api.mute_member(
            channel_id=channel_id,
            user_id=user_id,
            mute_seconds=mute_seconds
        )
    
    async def mute_all(self, channel_id: str, 
                        mute_end_timestamp: str = None,
                        mute_seconds: str = None) -> Any:
        """
        全员禁言
        
        Args:
            channel_id: 频道 ID
            mute_end_timestamp: 禁言结束时间戳
            mute_seconds: 禁言时长（秒）
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id}
        if mute_end_timestamp:
            params["mute_end_timestamp"] = mute_end_timestamp
        if mute_seconds:
            params["mute_seconds"] = mute_seconds
        return await self.client.api.mute_all(**params)
    
    async def delete_channel(self, channel_id: str) -> Any:
        """
        删除子频道
        
        Args:
            channel_id: 子频道 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_channel(channel_id=channel_id)
    
    async def get_guild_member(self, guild_id: str, user_id: str) -> Any:
        """
        获取频道成员详情
        
        Args:
            guild_id: 频道 ID
            user_id: 用户 ID
            
        Returns:
            成员信息
        """
        return await self.client.api.get_guild_member(
            guild_id=guild_id,
            user_id=user_id
        )
    
    async def post_reaction(self, channel_id: str, message_id: str,
                             emoji_type: int, emoji_id: str) -> Any:
        """
        发送表情回应
        
        Args:
            channel_id: 频道 ID
            message_id: 消息 ID
            emoji_type: 表情类型
            emoji_id: 表情 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.post_reaction(
            channel_id=channel_id,
            message_id=message_id,
            emoji_type=emoji_type,
            emoji_id=emoji_id
        )
    
    async def delete_reaction(self, channel_id: str, message_id: str,
                               emoji_type: int, emoji_id: str) -> Any:
        """
        删除表情回应
        
        Args:
            channel_id: 频道 ID
            message_id: 消息 ID
            emoji_type: 表情类型
            emoji_id: 表情 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_reaction(
            channel_id=channel_id,
            message_id=message_id,
            emoji_type=emoji_type,
            emoji_id=emoji_id
        )
    
    async def create_channel(self, guild_id: str, name: str, 
                              type_: int = 0, sub_type: int = 0,
                              parent_id: str = None, position: int = None) -> Any:
        """
        创建子频道
        
        Args:
            guild_id: 频道 ID
            name: 子频道名称
            type_: 子频道类型
            sub_type: 子频道子类型
            parent_id: 分组 ID
            position: 排序位置
            
        Returns:
            创建的子频道信息
        """
        params = {
            "guild_id": guild_id,
            "name": name,
            "type": type_,
            "sub_type": sub_type,
        }
        if parent_id:
            params["parent_id"] = parent_id
        if position is not None:
            params["position"] = position
        return await self.client.api.create_channel(**params)
    
    async def update_channel(self, channel_id: str, name: str = None,
                              position: int = None, parent_id: str = None) -> Any:
        """
        修改子频道
        
        Args:
            channel_id: 子频道 ID
            name: 新名称
            position: 新位置
            parent_id: 新分组 ID
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id}
        if name:
            params["name"] = name
        if position is not None:
            params["position"] = position
        if parent_id:
            params["parent_id"] = parent_id
        return await self.client.api.update_channel(**params)


class PermissionAdapter:
    """权限适配器"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_channel_permissions(self, channel_id: str, user_id: str) -> Any:
        """
        获取子频道权限
        
        Args:
            channel_id: 子频道 ID
            user_id: 用户 ID
            
        Returns:
            权限信息
        """
        return await self.client.api.get_channel_permissions(
            channel_id=channel_id,
            user_id=user_id
        )
    
    async def update_channel_permissions(self, channel_id: str, user_id: str,
                                          add: str = None, remove: str = None) -> Any:
        """
        修改子频道权限
        
        Args:
            channel_id: 子频道 ID
            user_id: 用户 ID
            add: 添加的权限
            remove: 移除的权限
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id, "user_id": user_id}
        if add:
            params["add"] = add
        if remove:
            params["remove"] = remove
        return await self.client.api.update_channel_permissions(**params)
    
    async def get_role_permissions(self, channel_id: str) -> Any:
        """
        获取子频道身份组权限
        
        Args:
            channel_id: 子频道 ID
            
        Returns:
            权限信息
        """
        return await self.client.api.get_channel_role_permissions(channel_id=channel_id)
    
    async def update_role_permissions(self, channel_id: str, 
                                       add: str = None, remove: str = None) -> Any:
        """
        修改子频道身份组权限
        
        Args:
            channel_id: 子频道 ID
            add: 添加的权限
            remove: 移除的权限
            
        Returns:
            API 响应
        """
        params = {"channel_id": channel_id}
        if add:
            params["add"] = add
        if remove:
            params["remove"] = remove
        return await self.client.api.update_channel_role_permissions(**params)


class GuildAdapter:
    """频道适配器"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_guild(self, guild_id: str) -> Any:
        """
        获取频道详情
        
        Args:
            guild_id: 频道 ID
            
        Returns:
            频道信息
        """
        return await self.client.api.get_guild(guild_id=guild_id)
    
    async def get_guild_channels(self, guild_id: str) -> Any:
        """
        获取频道子频道列表
        
        Args:
            guild_id: 频道 ID
            
        Returns:
            子频道列表
        """
        return await self.client.api.get_channels(guild_id=guild_id)
    
    async def get_guild_members(self, guild_id: str) -> Any:
        """
        获取频道成员列表
        
        Args:
            guild_id: 频道 ID
            
        Returns:
            成员列表
        """
        return await self.client.api.get_guild_members(guild_id=guild_id)
    
    async def delete_guild_member(self, guild_id: str, user_id: str,
                                    add_blacklist: bool = False,
                                    delete_history_msg_days: int = -1) -> Any:
        """
        删除频道成员
        
        Args:
            guild_id: 频道 ID
            user_id: 用户 ID
            add_blacklist: 是否加入黑名单
            delete_history_msg_days: 删除消息天数
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_guild_member(
            guild_id=guild_id,
            user_id=user_id,
            add_blacklist=add_blacklist,
            delete_history_msg_days=delete_history_msg_days
        )
    
    async def get_guild_roles(self, guild_id: str) -> Any:
        """
        获取频道身份组列表
        
        Args:
            guild_id: 频道 ID
            
        Returns:
            身份组列表
        """
        return await self.client.api.get_guild_roles(guild_id=guild_id)
    
    async def create_guild_role(self, guild_id: str, name: str, 
                                 color: int = 0, hoist: int = 0) -> Any:
        """
        创建频道身份组
        
        Args:
            guild_id: 频道 ID
            name: 身份组名称
            color: 颜色
            hoist: 是否单独展示
            
        Returns:
            创建的身份组信息
        """
        return await self.client.api.create_guild_role(
            guild_id=guild_id,
            name=name,
            color=color,
            hoist=hoist
        )
    
    async def update_guild_role(self, guild_id: str, role_id: str,
                                 name: str = None, color: int = None,
                                 hoist: int = None) -> Any:
        """
        修改频道身份组
        
        Args:
            guild_id: 频道 ID
            role_id: 身份组 ID
            name: 新名称
            color: 新颜色
            hoist: 是否单独展示
            
        Returns:
            API 响应
        """
        params = {"guild_id": guild_id, "role_id": role_id}
        if name:
            params["name"] = name
        if color is not None:
            params["color"] = color
        if hoist is not None:
            params["hoist"] = hoist
        return await self.client.api.update_guild_role(**params)
    
    async def delete_guild_role(self, guild_id: str, role_id: str) -> Any:
        """
        删除频道身份组
        
        Args:
            guild_id: 频道 ID
            role_id: 身份组 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_guild_role(
            guild_id=guild_id,
            role_id=role_id
        )
    
    async def add_guild_role_member(self, guild_id: str, role_id: str,
                                      user_id: str) -> Any:
        """
        添加身份组成员
        
        Args:
            guild_id: 频道 ID
            role_id: 身份组 ID
            user_id: 用户 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.create_guild_role_member(
            guild_id=guild_id,
            role_id=role_id,
            user_id=user_id
        )
    
    async def remove_guild_role_member(self, guild_id: str, role_id: str,
                                         user_id: str) -> Any:
        """
        删除身份组成员
        
        Args:
            guild_id: 频道 ID
            role_id: 身份组 ID
            user_id: 用户 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_guild_role_member(
            guild_id=guild_id,
            role_id=role_id,
            user_id=user_id
        )


class PinAdapter:
    """精华消息适配器"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_pins(self, channel_id: str) -> Any:
        """
        获取精华消息
        
        Args:
            channel_id: 频道 ID
            
        Returns:
            精华消息列表
        """
        return await self.client.api.get_pins(channel_id=channel_id)
    
    async def put_pin(self, channel_id: str, message_id: str) -> Any:
        """
        设置精华消息
        
        Args:
            channel_id: 频道 ID
            message_id: 消息 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.put_pin(
            channel_id=channel_id,
            message_id=message_id
        )
    
    async def delete_pin(self, channel_id: str, message_id: str) -> Any:
        """
        删除精华消息
        
        Args:
            channel_id: 频道 ID
            message_id: 消息 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_pin(
            channel_id=channel_id,
            message_id=message_id
        )


class AnnounceAdapter:
    """公告适配器"""
    
    def __init__(self, client):
        self.client = client
    
    async def create_guild_announce(self, guild_id: str, channel_id: str,
                                      message_id: str) -> Any:
        """
        创建频道公告
        
        Args:
            guild_id: 频道 ID
            channel_id: 子频道 ID
            message_id: 消息 ID
            
        Returns:
            API 响应
        """
        return await self.client.api.create_guild_announce(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id
        )
    
    async def delete_guild_announce(self, guild_id: str, message_id: str = "all") -> Any:
        """
        删除频道公告
        
        Args:
            guild_id: 频道 ID
            message_id: 消息 ID 或 "all"
            
        Returns:
            API 响应
        """
        return await self.client.api.delete_guild_announce(
            guild_id=guild_id,
            message_id=message_id
        )


class APIPermissionAdapter:
    """接口权限适配器"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_permissions(self, guild_id: str) -> Any:
        """
        获取频道可用权限列表
        
        Args:
            guild_id: 频道 ID
            
        Returns:
            权限列表
        """
        return await self.client.api.get_permissions(guild_id=guild_id)
    
    async def post_permission(self, guild_id: str, channel_id: str,
                               api_identify: str, desc: str) -> Any:
        """
        创建频道 API 权限授权链接
        
        Args:
            guild_id: 频道 ID
            channel_id: 子频道 ID
            api_identify: API 标识
            desc: 申请理由
            
        Returns:
            授权链接
        """
        return await self.client.api.post_permission_demand(
            guild_id=guild_id,
            channel_id=channel_id,
            api_identify=api_identify,
            desc=desc
        )


# 快捷创建所有适配器
def create_adapters(client) -> Dict[str, Any]:
    """
    创建所有适配器实例
    
    Args:
        client: botpy.Client 实例
        
    Returns:
        适配器字典
    """
    return {
        "action": ActionAdapter(client),
        "permission": PermissionAdapter(client),
        "guild": GuildAdapter(client),
        "pin": PinAdapter(client),
        "announce": AnnounceAdapter(client),
        "api_permission": APIPermissionAdapter(client),
    }
