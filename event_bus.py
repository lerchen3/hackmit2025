import json
import threading
import queue
import time
from typing import Dict, Any, List


class AgentEventBus:
    def __init__(self) -> None:
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: Dict[str, Any]) -> None:
        # non-blocking publish to all subscribers
        with self._lock:
            subs = list(self._subscribers)
        drop_list = []
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                # drop oldest to make room
                try:
                    _ = q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    drop_list.append(q)
            except Exception:
                drop_list.append(q)
        if drop_list:
            with self._lock:
                for q in drop_list:
                    if q in self._subscribers:
                        self._subscribers.remove(q)


agent_event_bus = AgentEventBus()


