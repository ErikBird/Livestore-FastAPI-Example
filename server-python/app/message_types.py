from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from datetime import datetime
import json


class SyncMetadata(BaseModel):
    created_at: str = Field(alias="createdAt")
    
    class Config:
        populate_by_name = True


class OptionMetadata(BaseModel):
    """Represents Effect's Option type for metadata"""
    tag: Literal["None", "Some"] = Field(alias="_tag")
    value: Optional[SyncMetadata] = None
    
    class Config:
        populate_by_name = True
    
    @classmethod
    def none(cls):
        return cls(_tag="None")
    
    @classmethod
    def some(cls, metadata: SyncMetadata):
        return cls(_tag="Some", value=metadata)


class EventEncoded(BaseModel):
    seq_num: int = Field(alias="seqNum")
    parent_seq_num: int = Field(alias="parentSeqNum") 
    name: str
    args: Optional[Any] = None
    client_id: str = Field(alias="clientId")
    session_id: str = Field(alias="sessionId")
    
    class Config:
        populate_by_name = True


class PullReq(BaseModel):
    tag: Literal["WSMessage.PullReq"] = Field(alias="_tag", default="WSMessage.PullReq")
    request_id: str = Field(alias="requestId")
    cursor: Optional[int] = None
    
    class Config:
        populate_by_name = True


class PullResBatchItem(BaseModel):
    event_encoded: EventEncoded = Field(alias="eventEncoded")
    metadata: OptionMetadata
    
    class Config:
        populate_by_name = True


class PullResRequestId(BaseModel):
    context: Literal["pull", "push"]
    request_id: str = Field(alias="requestId")
    
    class Config:
        populate_by_name = True


class PullRes(BaseModel):
    tag: Literal["WSMessage.PullRes"] = Field(alias="_tag", default="WSMessage.PullRes")
    batch: List[PullResBatchItem]
    request_id: PullResRequestId = Field(alias="requestId")
    remaining: int
    
    class Config:
        populate_by_name = True


class PushReq(BaseModel):
    tag: Literal["WSMessage.PushReq"] = Field(alias="_tag", default="WSMessage.PushReq")
    request_id: str = Field(alias="requestId")
    batch: List[EventEncoded]
    
    class Config:
        populate_by_name = True


class PushAck(BaseModel):
    tag: Literal["WSMessage.PushAck"] = Field(alias="_tag", default="WSMessage.PushAck")
    request_id: str = Field(alias="requestId")
    
    class Config:
        populate_by_name = True


class ErrorMessage(BaseModel):
    tag: Literal["WSMessage.Error"] = Field(alias="_tag", default="WSMessage.Error")
    request_id: str = Field(alias="requestId")
    message: str
    
    class Config:
        populate_by_name = True


class Ping(BaseModel):
    tag: Literal["WSMessage.Ping"] = Field(alias="_tag", default="WSMessage.Ping")
    request_id: Literal["ping"] = Field(alias="requestId", default="ping")
    
    class Config:
        populate_by_name = True


class Pong(BaseModel):
    tag: Literal["WSMessage.Pong"] = Field(alias="_tag", default="WSMessage.Pong")
    request_id: Literal["ping"] = Field(alias="requestId", default="ping")
    
    class Config:
        populate_by_name = True


class AdminResetRoomReq(BaseModel):
    tag: Literal["WSMessage.AdminResetRoomReq"] = Field(alias="_tag", default="WSMessage.AdminResetRoomReq")
    request_id: str = Field(alias="requestId")
    admin_secret: str = Field(alias="adminSecret")
    
    class Config:
        populate_by_name = True


class AdminResetRoomRes(BaseModel):
    tag: Literal["WSMessage.AdminResetRoomRes"] = Field(alias="_tag", default="WSMessage.AdminResetRoomRes")
    request_id: str = Field(alias="requestId")
    
    class Config:
        populate_by_name = True


class AdminInfoReq(BaseModel):
    tag: Literal["WSMessage.AdminInfoReq"] = Field(alias="_tag", default="WSMessage.AdminInfoReq")
    request_id: str = Field(alias="requestId")
    admin_secret: str = Field(alias="adminSecret")
    
    class Config:
        populate_by_name = True


class AdminInfoRes(BaseModel):
    tag: Literal["WSMessage.AdminInfoRes"] = Field(alias="_tag", default="WSMessage.AdminInfoRes")
    request_id: str = Field(alias="requestId")
    info: Dict[str, Any]
    
    class Config:
        populate_by_name = True


ClientToBackendMessage = Union[
    PullReq,
    PushReq,
    AdminResetRoomReq,
    AdminInfoReq,
    Ping
]

BackendToClientMessage = Union[
    PullRes,
    PushAck,
    AdminResetRoomRes,
    AdminInfoRes,
    ErrorMessage,
    Pong
]


def parse_client_message(data: str) -> ClientToBackendMessage:
    """Parse incoming WebSocket message from client"""
    msg_dict = json.loads(data)
    tag = msg_dict.get("_tag")
    
    if tag == "WSMessage.PullReq":
        return PullReq(**msg_dict)
    elif tag == "WSMessage.PushReq":
        return PushReq(**msg_dict)
    elif tag == "WSMessage.AdminResetRoomReq":
        return AdminResetRoomReq(**msg_dict)
    elif tag == "WSMessage.AdminInfoReq":
        return AdminInfoReq(**msg_dict)
    elif tag == "WSMessage.Ping":
        return Ping(**msg_dict)
    else:
        raise ValueError(f"Unknown message type: {tag}")


def encode_server_message(message: BackendToClientMessage) -> str:
    """Encode server message for sending to client"""
    return message.model_dump_json(by_alias=True, exclude_none=True)