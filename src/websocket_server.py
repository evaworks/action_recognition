"""WebSocket服务器模块 - 推送视频流"""
import asyncio
import base64
import json
import threading
from typing import Set, Optional
import cv2
import numpy as np


class WebSocketServer:
    """WebSocket视频流服务器"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set = set()
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_queue = asyncio.Queue(maxsize=2)
        self._jpeg_quality = 70
        self._loop = None
        
    def start(self) -> bool:
        """启动WebSocket服务器"""
        if self._running:
            return False
            
        self._running = True
        self._thread = threading.Thread(target=self._run_async_server, daemon=True)
        self._thread.start()
        print(f"WebSocket服务器已启动: ws://{self.host}:{self.port}")
        return True
        
    def _run_async_server(self) -> None:
        """在独立线程中运行异步服务器"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_server())
        
    async def _async_server(self) -> None:
        """异步WebSocket服务器"""
        try:
            import websockets
        except ImportError:
            print("websockets库未安装，请运行: pip install websockets")
            return
            
        async with websockets.serve(self._handle_client, self.host, self.port):
            while self._running:
                await asyncio.sleep(0.1)
                
    async def _handle_client(self, websocket) -> None:
        """处理客户端连接"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        print(f"WebSocket客户端连接: {client_addr}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    cmd = data.get('command')
                    
                    if cmd == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                    elif cmd == 'set_quality':
                        quality = data.get('quality', 70)
                        self._jpeg_quality = max(10, min(100, quality))
                        await websocket.send(json.dumps({
                            'type': 'response',
                            'success': True,
                            'quality': self._jpeg_quality
                        }))
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"WebSocket客户端断开: {client_addr}, {e}")
        finally:
            self.clients.discard(websocket)
            print(f"WebSocket客户端已断开: {client_addr}")
            
    def send_frame(self, frame: np.ndarray) -> None:
        """发送视频帧到所有客户端"""
        if not self.clients or frame is None:
            return
            
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            frame_data = {
                'type': 'frame',
                'data': frame_base64,
                'format': 'jpeg'
            }
            
            frame_json = json.dumps(frame_data)
            
            asyncio.run_coroutine_threadsafe(
                self._broadcast_frame(frame_json), 
                self._loop
            )
            
        except Exception as e:
            pass
            
    async def _broadcast_frame(self, frame_json: str) -> None:
        """广播帧到所有客户端"""
        if not self.clients:
            return
            
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(frame_json)
            except Exception:
                disconnected.add(client)
                
        for client in disconnected:
            self.clients.discard(client)
            
    def stop(self) -> None:
        """停止WebSocket服务器"""
        self._running = False
        if self._server:
            self._server.close()
        print("WebSocket服务器已停止")
        
    def get_client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.clients)


class WebSocketClient:
    """WebSocket客户端（用于测试或级联）"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self._connected = False
        self._callbacks = []
        
    def connect(self) -> bool:
        """连接WebSocket服务器"""
        try:
            import websockets
            import asyncio
            
            async def _connect():
                self._ws = await websockets.connect(self.uri)
                self._connected = True
                
            asyncio.run(_connect())
            return True
        except Exception as e:
            print(f"WebSocket连接失败: {e}")
            return False
            
    def on_frame(self, callback) -> None:
        """注册帧回调"""
        self._callbacks.append(callback)
        
    def receive_loop(self) -> None:
        """接收视频流循环"""
        import asyncio
        
        async def _receive():
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'frame':
                        frame_base64 = data.get('data')
                        frame_bytes = base64.b64decode(frame_base64)
                        nparr = np.frombuffer(frame_bytes, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        for callback in self._callbacks:
                            callback(frame)
                except Exception:
                    pass
                    
        asyncio.run(_receive())
        
    def disconnect(self) -> None:
        """断开连接"""
        if self._connected:
            import asyncio
            asyncio.run(self._ws.close())
            self._connected = False
