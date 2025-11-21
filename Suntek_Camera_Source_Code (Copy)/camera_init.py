import multiprocessing, queue, threading, sys
import signal
import time
import logging
from camera_frame import suntek_camera_init, get_options
from camera_settings import suntek_camera_settings_init
from interthread_signal import inter_thread

logging.basicConfig(level=logging.INFO)

class CameraProcessController:
    def __init__(self, wdevice, wwidth, wheight, wangle, wflip, wcolormap):
        self.proc = None
        self.device=wdevice
        self.width=wwidth
        self.height=wheight
        self.angle=wangle
        self.flip=wflip
        self.colormap=wcolormap

    def start(self):
        self.close()  # Ensure old process is cleaned up
        self.proc = multiprocessing.Process(target=suntek_camera_init, name="CameraProcess", args=(self.device,self.width,self.height,self.angle, self.flip, self.colormap,))
        self.proc.start()
        logging.info(f"[Camera] Started PID {self.proc.pid}")

    def close(self):
        if self.proc and self.proc.is_alive():
            logging.info(f"[Camera] Terminating PID {self.proc.pid}")
            self.proc.kill()
            self.proc.join(timeout=0.1)
        self.proc = None


device, width, height, angle, flip, colormap=get_options()
camera_ctrl = CameraProcessController(device, width, height, angle, flip, colormap)

def shutdown_handler(signum, frame):
    logging.info("Shutting down...")
    camera_ctrl.close()
    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

def switch_physical_camera(msg):
    global camera_ctrl
    if msg["format"].find('dev') != -1:
        time.sleep(0.5)
        camera_ctrl=CameraProcessController(msg["format"], width, height, angle, flip, colormap)
        camera_ctrl.start()

def monitor_msg_queue():
    while(1):
        #print("monitoring..")
        try:
            msg = inter_thread.get_nowait()
            #print(msg)
            if msg["action"] == "psettingchange":
                camera_ctrl.close()
                switch_physical_camera(msg)
            if msg["action"] == "psettingchanged":
                camera_ctrl.start()
        except queue.Empty:
            pass
        finally:
            time.sleep(0.1)


def main():

    # Start both processes
    camera_ctrl.start()
    #settings_ctrl.start()
    
    t2 = threading.Thread(target=suntek_camera_settings_init)
    t2.start()

    t3 = threading.Thread(target=monitor_msg_queue)
    t3.start()
    #monitor_queue.start()

    try:
        while True:
            t2.join()
            t3.join()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler(None, None)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        multiprocessing.set_start_method("spawn", force=False)
    except RuntimeError:
        # It's already set — safe to ignore if it's already "spawn"
        pass # Required on Windows/macOS
    sys.exit(main())
