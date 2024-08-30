"""GUI Application for blink detection and seed identification"""
try:
    import heapq
    import json
    import os.path
    import os
    # solves camera start up issues, must be done before importing cv2
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
    import cv2
    import rngtool
    import signal
    import sys
    import threading
    import time
    import tkinter as tk
    import tkinter.filedialog as fd
    from pyautogui import press
    from tkinter import ttk
    from os import listdir
    from os.path import isfile, join
    from PIL import Image, ImageTk
    from xorshift import Xorshift
except ImportError as import_fail:
    raise \
    Exception("Could not import the required modules, " \
              "make sure you are running with the correct python version, " \
              "and that packages are installed correctly.") \
    from import_fail

version = sys.version_info
if version[0] < 3 or version[1] < 7:
    raise Exception("Python 版本不正确，请确保使用 3.7 或更高版本运行")

os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# pylint: disable=too-many-instance-attributes
# this many instance attributes are appropriate
class PlayerBlinkGUI(tk.Frame):
    """GUI Application for blink detection and seed identification"""
    default_config = {
        "MonitorWindow": True,
        "WindowPrefix": "SysDVR-Client [PID ",
        "image": "./images/cave/eye.png",
        "view": [0, 0, 40, 40],
        "thresh": 0.9,
        "white_delay": 0.0,
        "advance_delay": 0,
        "advance_delay_2": 0,
        "npc": 0,
        "timeline_npc": 0,
        "pokemon_npc": 0,
        "crop": [0, 0, 0, 0],
        "camera": 0,
        "display_percent": 80,
        "reident_1_pk_npc": False,
        "final_a_press_delay": 84,
        "timeline_buffer": 110,
        }
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.rng = None
        self.player_eye = None
        self.player_eye_tk = None
        self.monitoring_thread = None
        self.reidentifying_thread = None
        self.tidsiding_thread = None
        self.previewing_thread = None
        self.monitor_tk_buffer = None
        self.monitor_tk = None
        self.raw_screenshot = None
        self.previewing = False
        self.monitoring = False
        self.reidentifying = False
        self.tidsiding = False
        self.timelining = False
        self.tracking = False
        self.advances = 0
        self.count_down = 0
        self.timeline_start = 0
        self.config_json = {}
        self.config_jsons = []
        self.pack()
        self.create_widgets()
        signal.signal(signal.SIGINT, self.__signal_handler)

    def update_configs(self,_=None):
        """Update the config names in config_combobox to all files in the config directory"""
        self.config_jsons = [f for f in listdir("configs") if isfile(join("configs", f))]
        self.config_combobox['values'] = self.config_jsons

    # pylint: disable=too-many-statements
    # does not need to be split
    def create_widgets(self):
        """Create and set up all of the widgets that are displayed in the application"""
        self.master.title("BDSP眨眼测试")

        ttk.Label(self,text="进度:").grid(column=0,row=0)
        ttk.Label(self,text="Seed[0-3]:").grid(column=0,row=3)
        ttk.Label(self,text="Seed[0-1]:").grid(column=0,row=7)
        ttk.Label(self,text="帧数:").grid(column=0,row=10)
        ttk.Label(self,text="计时器:").grid(column=0,row=11)
        ttk.Label(self,text="手动前进帧数:").grid(column=0,row=12)
        ttk.Label(self,text="按键前进帧数:").grid(column=0,row=14)
        ttk.Label(self,text="窗口显示百分比").grid(column=0,row=15)

        self.auto_timeline_check_var = tk.IntVar()
        self.auto_timeline_check = ttk.Checkbutton(self, text="自动进行时间线", \
            variable=self.auto_timeline_check_var)
        self.auto_timeline_check.grid(column=0,row=17,columnspan=2)
        ttk.Label(self,text="目标帧数:").grid(column=0,row=18)
        self.target_advances = tk.Spinbox(self, from_= 0, to = 99999, width = 20)
        self.target_advances.grid(column=1,row=18)
        ttk.Label(self,text="按A帧数的延迟:").grid(column=0,row=19)
        self.final_a_press_delay = tk.Spinbox(self, from_= 0, to = 99999, width = 20)
        self.final_a_press_delay.grid(column=1,row=19)
        ttk.Label(self,text="过帧延迟:").grid(column=0,row=20)
        self.timeline_buffer = tk.Spinbox(self, from_= 0, to = 99999, width = 20)
        self.timeline_buffer.grid(column=1,row=20)
        ttk.Label(self,text="开始按下时间线的帧数:").grid(column=0,row=21)
        self.timeline_start_label = ttk.Label(self,text=self.timeline_start)
        self.timeline_start_label.grid(column=1,row=21)
        ttk.Label(self,text="最后按A的帧数:").grid(column=0,row=22)
        self.press_a_label = ttk.Label(self,text=0)
        self.press_a_label.grid(column=1,row=22)

        self.progress = ttk.Label(self,text="0/0")
        self.progress.grid(column=1,row=0)

        self.config_combobox = ttk.Combobox(self, state="readonly", values=[])
        self.config_combobox.grid(column=2,row=0)
        self.config_combobox.bind("<<ComboboxSelected>>", self.config_combobox_onchange)
        self.config_combobox.bind("<Button-1>", self.update_configs)
        self.update_configs()

        self.new_config_button = ttk.Button(self,text="+",command=self.new_config,width=2)
        self.new_config_button.grid(column=3,row=0,columnspan=2)

        self.eye_display = ttk.Label(self)
        self.eye_display.grid(column=2,row=1)

        self.prefix_input = ttk.Entry(self)
        self.prefix_input.grid(column=2,row=2)

        ttk.Label(self,text="摄像头选择:").grid(column=3,row=1)
        self.camera_index = tk.Spinbox(self, from_= 0, to = 99, width = 5)
        self.camera_index.grid(column=4,row=1)

        self.monitor_window_var = tk.IntVar()
        self.monitor_window = ttk.Checkbutton(self,text="投影窗口", \
            variable=self.monitor_window_var)
        self.monitor_window.grid(column=3,row=2,columnspan=2)

        self.monitor_display_buffer = ttk.Label(self)
        self.monitor_display_buffer.grid(column=2,row=3,rowspan=64,columnspan=2)
        self.monitor_display = ttk.Label(self)
        self.monitor_display.grid(column=2,row=3,rowspan=64,columnspan=2)

        self.monitor_blink_button = ttk.Button(self, text="捕捉眨眼", \
            command=self.monitor_blinks)
        self.monitor_blink_button.grid(column=5,row=0)

        self.reidentify_button = ttk.Button(self, text="重新检测", command=self.reidentify)
        self.reidentify_button.grid(column=5,row=1)

        self.preview_button = ttk.Button(self, text="预览画面", command=self.preview)
        self.preview_button.grid(column=5,row=2)

        self.stop_tracking_button = ttk.Button(self, text="停止所有进程", \
            command=self.stop_tracking)
        self.stop_tracking_button.grid(column=5,row=3)

        self.timeline_button = ttk.Button(self, text="时间线", command=self.timeline)
        self.timeline_button.grid(column=5,row=4)

        self.tidsid_button = ttk.Button(self, text="TID/SID", command=self.tidsid)
        self.tidsid_button.grid(column=5,row=5)

        ttk.Label(self,text="测眨眼框X轴").grid(column=6,row=1)
        ttk.Label(self,text="测眨眼框Y轴").grid(column=6,row=2)
        ttk.Label(self,text="测眨眼框宽度").grid(column=6,row=3)
        ttk.Label(self,text="测眨眼框长度").grid(column=6,row=4)
        ttk.Label(self,text="阈值").grid(column=6,row=5)
        ttk.Label(self,text="时间延迟").grid(column=6,row=6)
        ttk.Label(self,text="帧数延迟").grid(column=6,row=7)
        ttk.Label(self,text="帧数延迟2").grid(column=6,row=8)
        ttk.Label(self,text="NPC数量").grid(column=6,row=9)
        ttk.Label(self,text="时间线上的NPC数量").grid(column=6,row=10)
        ttk.Label(self,text="宝可梦NPC数量").grid(column=6,row=11)

        self.menu_check_var = tk.IntVar()
        self.menu_check = ttk.Checkbutton(self, text="关闭文本框时+1", \
            variable=self.menu_check_var)
        self.menu_check.grid(column=7,row=0)
        self.menu_check_var.set(1)

        self.reident_noisy_check_var = tk.IntVar()
        self.reident_noisy_check = ttk.Checkbutton(self, text="重新检测 1 PK NPC", \
            variable=self.reident_noisy_check_var)
        self.reident_noisy_check.grid(column=5,row=6)
        self.reident_noisy_check_var.set(0)

        ttk.Label(self,text="重新检测最小值:").grid(column=4,row=7)
        self.reident_min = tk.Spinbox(self, from_= 0, to = 9999999999)
        self.reident_min.grid(column=5,row=7)
        ttk.Label(self,text="重新检测最大值:").grid(column=4,row=8)
        self.reident_max = tk.Spinbox(self, from_= 0, to = 9999999999)
        self.reident_max.grid(column=5,row=8)
        self.reident_max.delete(0, tk.END)
        self.reident_max.insert(0, 1000000)

        self.pos_x = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_x.grid(column=7,row=1)
        self.pos_y = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_y.grid(column=7,row=2)
        self.pos_w = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_w.grid(column=7,row=3)
        self.pos_h = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_h.grid(column=7,row=4)
        self.pos_th = tk.Spinbox(self, from_= 0, to = 1, width = 5, increment=0.1)
        self.pos_th.grid(column=7,row=5)
        self.whi_del = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=0.1)
        self.whi_del.grid(column=7,row=6)
        self.adv_del = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.adv_del.grid(column=7,row=7)
        self.adv_del_2 = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.adv_del_2.grid(column=7,row=8)
        self.npc = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.npc.grid(column=7,row=9)
        self.timeline_npc = tk.Spinbox(self, from_= -1, to = 999, width = 5, increment=1)
        self.timeline_npc.grid(column=7,row=10)
        self.pokemon_npc = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.pokemon_npc.grid(column=7,row=11)

        self.new_eye_button = ttk.Button(self, text="更换眼睛图片", command=self.new_eye)
        self.new_eye_button.grid(column=6,row=12,columnspan=2)

        self.save_button = ttk.Button(self, text="保存当前配置", command=self.save_config)
        self.save_button.grid(column=6,row=13,columnspan=2)

        self.raw_screenshot_button = ttk.Button(self, text="自动识别裁剪画面眼睛", \
            command=self.save_screenshot)
        self.raw_screenshot_button.grid(column=6,row=14,columnspan=2)

        self.s0_1_2_3 = tk.Text(self, width=10, height=4)
        self.s0_1_2_3.grid(column=1,row=2,rowspan=4)

        self.s01_23 = tk.Text(self, width=20, height=2)
        self.s01_23.grid(column=1,row=6,rowspan=4)

        self.advances = 0
        self.adv = ttk.Label(self,text=self.advances)
        self.adv.grid(column=1,row=10)

        self.count_down = 0
        self.count_down_label = ttk.Label(self,text=self.count_down)
        self.count_down_label.grid(column=1,row=11)

        self.advances_increase = tk.Spinbox(self, from_ = 0, to = 999999)
        self.advances_increase.grid(column=1,row=12)

        self.advances_increase_button = ttk.Button(self, text="点击手动前进帧数", \
            command=self.increase_advances)
        self.advances_increase_button.grid(column=1,row=13)

        self.keypress_advance = tk.Spinbox(self, from_ = 0, to = 999999)
        self.keypress_advance.grid(column=1,row=14)

        self.display_percent = tk.Spinbox(self, from_ = 0, to = 500)
        self.display_percent.grid(column=1,row=15)

        self.pos_x.delete(0, tk.END)
        self.pos_x.insert(0, 0)
        self.pos_y.delete(0, tk.END)
        self.pos_y.insert(0, 0)
        self.pos_w.delete(0, tk.END)
        self.pos_w.insert(0, 40)
        self.pos_h.delete(0, tk.END)
        self.pos_h.insert(0, 40)
        self.pos_th.delete(0, tk.END)
        self.pos_th.insert(0, 0.9)
        self.whi_del.delete(0, tk.END)
        self.whi_del.insert(0, 0.0)
        self.adv_del.delete(0, tk.END)
        self.adv_del.insert(0, 0)
        self.adv_del_2.delete(0, tk.END)
        self.adv_del_2.insert(0, 0)
        self.npc.delete(0, tk.END)
        self.npc.insert(0, 0)
        self.timeline_npc.delete(0, tk.END)
        self.timeline_npc.insert(0, 0)
        self.pokemon_npc.delete(0, tk.END)
        self.pokemon_npc.insert(0, 0)
        self.camera_index.delete(0, tk.END)
        self.camera_index.insert(0, 0)
        self.advances_increase.delete(0, tk.END)
        self.advances_increase.insert(0, 165)
        self.keypress_advance.delete(0, tk.END)
        self.keypress_advance.insert(0, -1)
        self.display_percent.delete(0, tk.END)
        self.display_percent.insert(0, 100)
        self.final_a_press_delay.delete(0, tk.END)
        self.final_a_press_delay.insert(0, 0)
        self.timeline_buffer.delete(0, tk.END)
        self.timeline_buffer.insert(0, 0)
        self.reident_noisy_check_var.set(False)

        self.after_task()

    def increase_advances(self):
        """Advance the rng and advance value by the amount specified in the gui"""
        plus = int(self.advances_increase.get())
        self.rng.advance(plus)
        self.advances += plus

    def new_config(self):
        """Create a new config file"""
        with fd.asksaveasfile(initialdir="./configs/", filetypes=[("JSON", ".json")]) as file:
            json.dump(self.default_config,file,indent=4)
            self.config_combobox.set(os.path.basename(file.name))
        self.config_combobox_onchange()

    def save_screenshot(self):
        """Save a raw screenshot of the current output for cropping an eye image"""
        with fd.asksaveasfile(initialdir="./", filetypes=[("PNG", ".png")]) as file:
            name = file.name
            if not name.endswith(".png"):
                name += ".png" # why doesnt filedialogue do this automatically?
            cv2.imwrite(name,self.raw_screenshot)

    def new_eye(self):
        """Select a new eye image"""
        self.config_json["image"] = "./" + \
            os.path.relpath(fd.askopenfilename(initialdir="./images/", \
            filetypes=[("Image", ".png")])).replace("\\","/")
        self.player_eye = cv2.imread(self.config_json["image"], cv2.IMREAD_GRAYSCALE)
        self.player_eye_tk = self.cv_image_to_tk(self.player_eye)
        self.eye_display['image'] = self.player_eye_tk

    def save_config(self):
        """Save current settings to the selected config file"""
        with open(join("configs",self.config_combobox.get()),"w",encoding="utf-8") as file:
            json.dump(self.config_json,file,indent=4)

    @staticmethod
    def cv_image_to_tk(image):
        """Convert a cv2 image for use in tkinter"""
        split = cv2.split(image)
        if len(split) == 3:
            blue,green,red = split
            image = cv2.merge((red,green,blue))
        image = Image.fromarray(image)
        return ImageTk.PhotoImage(image=image)

    def config_combobox_onchange(self, _=None):
        """Update config_json and settings widgets when the selected config changes"""
        with open(join("configs",self.config_combobox.get()),encoding="utf-8") as file:
            self.config_json = json.load(file)
        missing = set(self.default_config.keys()).difference(self.config_json.keys())
        if len(missing) > 0:
            print(f"Config was missing the following keys {missing}\nDefaults have been added")
        for key in missing:
            self.config_json[key] = self.default_config[key]
        self.pos_x.delete(0, tk.END)
        self.pos_x.insert(0, self.config_json["view"][0])
        self.pos_y.delete(0, tk.END)
        self.pos_y.insert(0, self.config_json["view"][1])
        self.pos_w.delete(0, tk.END)
        self.pos_w.insert(0, self.config_json["view"][2])
        self.pos_h.delete(0, tk.END)
        self.pos_h.insert(0, self.config_json["view"][3])
        self.pos_th.delete(0, tk.END)
        self.pos_th.insert(0, self.config_json["thresh"])
        self.whi_del.delete(0, tk.END)
        self.whi_del.insert(0, self.config_json["white_delay"])
        self.adv_del.delete(0, tk.END)
        self.adv_del.insert(0, self.config_json["advance_delay"])
        self.adv_del_2.delete(0, tk.END)
        self.adv_del_2.insert(0, self.config_json["advance_delay_2"])
        self.npc.delete(0, tk.END)
        self.npc.insert(0, self.config_json["npc"])
        self.pokemon_npc.delete(0, tk.END)
        self.pokemon_npc.insert(0, self.config_json["pokemon_npc"])
        self.timeline_npc.delete(0, tk.END)
        self.timeline_npc.insert(0, self.config_json["timeline_npc"])
        self.camera_index.delete(0, tk.END)
        self.camera_index.insert(0, self.config_json["camera"])
        self.player_eye = cv2.imread(self.config_json["image"], cv2.IMREAD_GRAYSCALE)
        self.player_eye_tk = self.cv_image_to_tk(self.player_eye)
        self.eye_display['image'] = self.player_eye_tk
        self.prefix_input.delete(0, tk.END)
        self.prefix_input.insert(0, self.config_json["WindowPrefix"])
        self.monitor_window_var.set(self.config_json["MonitorWindow"])
        self.display_percent.delete(0, tk.END)
        self.display_percent.insert(0, self.config_json["display_percent"])
        self.final_a_press_delay.delete(0, tk.END)
        self.final_a_press_delay.insert(0, self.config_json["final_a_press_delay"])
        self.timeline_buffer.delete(0, tk.END)
        self.timeline_buffer.insert(0, self.config_json["timeline_buffer"])
        self.reident_noisy_check_var.set(self.config_json["reident_1_pk_npc"])

    def stop_tracking(self):
        """Set tracking to False"""
        self.tracking = False

    def timeline(self):
        """Set timeline to True"""
        self.timelining = True

    def monitor_blinks(self):
        """Start monitoring 40 blinks to deduce current state"""
        if not self.monitoring:
            self.monitor_blink_button['text'] = "停止捕捉眨眼"
            self.monitoring = True
            self.monitoring_thread=threading.Thread(target=self.monitoring_work)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
        else:
            self.monitor_blink_button['text'] = "捕捉眨眼"
            self.monitoring = False

    def reidentify(self):
        """Start monitoring 7/20 blinks to deduce current advance based on entered state"""
        if not self.reidentifying:
            self.reidentify_button['text'] = "停止重新检测"
            self.reidentifying = True
            self.reidentifying_thread=threading.Thread(target=self.reidentifying_work)
            self.reidentifying_thread.daemon = True
            self.reidentifying_thread.start()
        else:
            self.reidentify_button['text'] = "重新检测"
            self.reidentifying = False

    def tidsid(self):
        """Start monitoring 64 munchlax blinks to deduce current state for tid/sid rng"""
        if not self.tidsiding:
            self.tidsid_button['text'] = "停止TID/SID"
            self.tidsiding = True
            self.tidsiding_thread=threading.Thread(target=self.tidsiding_work)
            self.tidsiding_thread.daemon = True
            self.tidsiding_thread.start()
        else:
            self.tidsid_button['text'] = "TID/SID"
            self.tidsiding = False

    # pylint: disable=too-many-branches
    # as this function handles both monitoring and setting up timelines
    # the amount of branches is fair
    def monitoring_work(self):
        """Thread work to be for the monitoring function"""
        self.tracking = False
        blinks, \
        intervals, \
        offset_time = rngtool.tracking_blink(self.player_eye,
                                            *self.config_json["view"],
                                            monitor_window=self.config_json["MonitorWindow"],
                                            window_prefix=self.config_json["WindowPrefix"],
                                            crop=self.config_json["crop"],
                                            camera=self.config_json["camera"],
                                            tk_window=self,
                                            threshold=self.config_json["thresh"])
        try:
            self.rng = rngtool.recov(blinks, intervals, npc=self.config_json["npc"])
        except AssertionError as failed_deduction:
            raise Exception("无法从捕捉眨眼中来推算seed") from failed_deduction

        self.monitor_blink_button['text'] = "捕捉眨眼"
        self.monitoring = False
        self.preview()

        waituntil = time.perf_counter()
        diff = round(waituntil-offset_time)
        self.rng.get_next_rand_sequence(diff
            * (self.config_json["npc"] + 1))

        state = self.rng.get_state()

        print(f"{state[0]:08X}{state[1]:08X} {state[2]:08X}{state[3]:08X}")
        print(f"{state[0]:08X} {state[1]:08X} {state[2]:08X} {state[3]:08X}")
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,f"{state[0]:08X}\n{state[1]:08X}\n{state[2]:08X}\n{state[3]:08X}")
        self.s01_23.insert(1.0,f"{state[0]:08X}{state[1]:08X}\n{state[2]:08X}{state[3]:08X}")

        self.advances = (1 if self.menu_check_var.get() else 0)
        self.tracking = True
        self.count_down = None
        while self.tracking:
            if self.count_down is None:
                if self.timelining:
                    self.count_down = 10
            elif self.count_down != 0:
                self.count_down -= 1
                print(self.count_down+1)
            else:
                break

            self.advances += self.config_json["npc"]+1
            if self.advances == int(self.keypress_advance.get()):
                press("pgup")
                print("Pressing pgup")
            rand = self.rng.get_next_rand_sequence(self.config_json["npc"]+1)[-1]
            waituntil += 1.018

            print(f"advances:{self.advances}, blinks:{hex(rand&0xF)}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)
        if self.timelining:
            self.rng.next()
            if self.menu_check_var.get():
                self.rng.next()
            # white screen
            time.sleep(self.config_json["white_delay"])
            waituntil = time.perf_counter()
            self.rng.advance(self.config_json["advance_delay"])
            self.advances += self.config_json["advance_delay"]
            print("blink timeline started")
            queue = []
            for _ in range(self.config_json["timeline_npc"]+1):
                heapq.heappush(queue, (waituntil+1.017,0))
            for _ in range(self.config_json["pokemon_npc"]):
                rand = self.rng.rangefloat(3,12) + 0.285
                heapq.heappush(queue, (waituntil+rand,1))

            self.count_down = 10
            while queue and self.tracking:
                self.advances += 1
                if self.auto_timeline_check_var.get() \
                  and self.advances == self.timeline_start:
                    self.timelining = True
                    print("Auto starting timeline")
                if self.advances == int(self.keypress_advance.get()):
                    press("pgup")
                    print("Pressing pgup")
                wait, advance_type = heapq.heappop(queue)
                next_time = wait - time.perf_counter() or 0
                if next_time>0:
                    time.sleep(next_time)

                if self.config_json["advance_delay_2"] != 0:
                    if self.count_down > 0:
                        self.count_down -= 1
                        print(self.count_down+1)
                    elif self.count_down != -1:
                        self.count_down -= 1
                        self.advances += self.config_json["advance_delay_2"]
                        self.rng.advance(self.config_json["advance_delay_2"])

                if advance_type==0:
                    rand = self.rng.next()
                    print(f"advances:{self.advances}, blink:{hex(rand&0xF)}")
                    heapq.heappush(queue, (wait+1.017, 0))
                else:
                    rand = self.rng.rangefloat(3,12) + 0.285

                    heapq.heappush(queue, (wait+rand, 1))
                    print(f"advances:{self.advances}, interval:{rand}")
            self.timelining = False

    def tidsiding_work(self):
        """Thread work to be done for the tidsid function"""
        self.tracking = False
        munchlax_intervals \
            = rngtool.tracking_poke_blink(self.player_eye,
                                          *self.config_json["view"],
                                          monitor_window=self.config_json["MonitorWindow"],
                                          window_prefix=self.config_json["WindowPrefix"],
                                          crop=self.config_json["crop"],
                                          camera=self.config_json["camera"],
                                          tk_window=self,
                                          threshold=self.config_json["thresh"],
                                          size=64)
        try:
            self.rng = rngtool.recov_by_munchlax(munchlax_intervals)
        except (AssertionError,IndexError) as failed_deduction:
            raise Exception("无法从捕捉眨眼中来推算seed") from failed_deduction
        state = self.rng.get_state()

        self.tidsid_button['text'] = "TID/SID"
        self.tidsiding = False
        self.preview()

        print(f"{state[0]:08X}{state[1]:08X} {state[2]:08X}{state[3]:08X}")
        print(f"{state[0]:08X} {state[1]:08X} {state[2]:08X} {state[3]:08X}")
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,f"{state[0]:08X}\n{state[1]:08X}\n{state[2]:08X}\n{state[3]:08X}")
        self.s01_23.insert(1.0,f"{state[0]:08X}{state[1]:08X}\n{state[2]:08X}{state[3]:08X}")

        waituntil = time.perf_counter()
        timestamp = time.time()

        print([hex(x) for x in state],timestamp)
        self.tracking = True
        while self.tracking:
            self.advances += 1
            interval = self.rng.rangefloat(3.0,12.0) + 0.285
            waituntil += interval

            print(f"advances:{self.advances}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)

    def reidentifying_work(self):
        """Thread work to be done for the reidentify function"""
        # pylint: disable=too-many-locals
        self.tracking = False
        try:
            state = [int(x,16) for x in self.s0_1_2_3.get(1.0,tk.END).split("\n")[:4]]
        except ValueError as bad_input:
            raise Exception("无法从Seed[0-3]中拉取seed进行重新检测" \
                            "请确保它们是十六进制格式并以行分隔") from bad_input

        print(f"{state[0]:08X}{state[1]:08X} {state[2]:08X}{state[3]:08X}")
        print(f"{state[0]:08X} {state[1]:08X} {state[2]:08X} {state[3]:08X}")
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,f"{state[0]:08X}\n{state[1]:08X}\n{state[2]:08X}\n{state[3]:08X}")
        self.s01_23.insert(1.0,f"{state[0]:08X}{state[1]:08X}\n{state[2]:08X}{state[3]:08X}")

        reident_range = int(self.reident_max.get()) - int(self.reident_min.get())
        if self.reident_noisy_check_var.get():
            if reident_range > 100000:
                cont = tk.messagebox.askyesno("警告",
                    f"重新检测的范围是 {reident_range} " \
                    "这超过了单个NPC建议的限制100000（即100k），" \
                    "结果可能不准确，是否继续？")
                if not cont:
                    return
            self.pokemon_npc.delete(0,tk.END)
            self.pokemon_npc.insert(0,1)
            _, \
            observed_intervals, \
            offset_time = rngtool.tracking_blink(self.player_eye,
                                                 *self.config_json["view"],
                                                 monitor_window=self.config_json["MonitorWindow"],
                                                 window_prefix=self.config_json["WindowPrefix"],
                                                 crop=self.config_json["crop"],
                                                 camera=self.config_json["camera"],
                                                 tk_window=self,
                                                 threshold=self.config_json["thresh"],
                                                 size=20)
            try:
                self.rng, adv = rngtool.reidentiy_by_intervals_noisy(Xorshift(*state),
                                                                   observed_intervals,
                                                                   search_min= \
                                                                       int(self.reident_min.get()),
                                                                   search_max= \
                                                                       int(self.reident_max.get()))
            except (TypeError,ValueError) as failed_deduction:
                raise Exception("无法从记录的眨眼动作中重新检测出结果") \
                    from failed_deduction
            self.timelining = True
            self.count_down = 0
        else:
            if reident_range > 1000000:
                cont = tk.messagebox.askyesno("警告",
                    f"重新检测的范围是 {reident_range} " \
                    "这超过了正常重新检测建议的限制1000000（即100万）" \
                    "结果可能不准确，是否继续？")
                if not cont:
                    return
            _, \
            observed_intervals, \
            offset_time = rngtool.tracking_blink(self.player_eye,
                                                 *self.config_json["view"],
                                                 monitor_window=self.config_json["MonitorWindow"],
                                                 window_prefix=self.config_json["WindowPrefix"],
                                                 crop=self.config_json["crop"],
                                                 camera=self.config_json["camera"],
                                                 tk_window=self,
                                                 threshold=self.config_json["thresh"],
                                                 size=7)
            try:
                self.rng, adv = rngtool.reidentiy_by_intervals(Xorshift(*state),
                                                              observed_intervals,
                                                              return_advance=True,
                                                              npc=self.config_json["npc"],
                                                              search_min= \
                                                                  int(self.reident_min.get()),
                                                              search_max= \
                                                                  int(self.reident_max.get()))
            except TypeError as failed_deduction:
                raise Exception("无法从记录的眨眼动作中重新检测出结果") \
                    from failed_deduction

        self.reidentify_button['text'] = "重新检测"
        self.reidentifying = False
        self.preview()

        waituntil = time.perf_counter()
        diff = round(waituntil-offset_time)
        self.rng.get_next_rand_sequence(diff
            * (self.config_json["npc"] + 1))
        state = self.rng.get_state()

        self.advances = adv \
            + diff \
            * (self.config_json["npc"] + 1) \
            + (1 if self.menu_check_var.get() else 0)
        self.tracking = True
        if not self.reident_noisy_check_var.get():
            self.count_down = None
        while self.tracking:
            if self.count_down is None:
                if self.timelining:
                    self.count_down = 10
            elif self.count_down != 0:
                self.count_down -= 1
                print(self.count_down+1)
            else:
                break

            self.advances += self.config_json["npc"]+1
            if self.auto_timeline_check_var.get() \
              and self.advances == self.timeline_start:
                self.timelining = True
                print("Auto starting timeline")
            if self.advances == int(self.keypress_advance.get()):
                press("pgup")
                print("Pressing pgup")
            rand = self.rng.get_next_rand_sequence(self.config_json["npc"]+1)[-1]
            waituntil += 1.018

            print(f"advances:{self.advances}, blinks:{hex(rand&0xF)}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)
        if self.timelining:
            self.rng.next()
            if self.menu_check_var.get():
                self.rng.next()
            # white screen
            time.sleep(self.config_json["white_delay"])
            waituntil = time.perf_counter()
            self.rng.advance(self.config_json["advance_delay"])
            self.advances += self.config_json["advance_delay"]
            print("blink timeline started")
            queue = []
            for _ in range(self.config_json["timeline_npc"]+1):
                heapq.heappush(queue, (waituntil+1.017,0))
            for _ in range(self.config_json["pokemon_npc"]):
                rand = self.rng.rangefloat(3,12) + 0.285
                heapq.heappush(queue, (waituntil+rand,1))

            self.count_down = 10
            while queue and self.tracking:
                self.advances += 1
                wait, advance_type = heapq.heappop(queue)
                next_time = wait - time.perf_counter() or 0
                if next_time>0:
                    time.sleep(next_time)

                if self.config_json["advance_delay_2"] != 0:
                    if self.count_down > 0:
                        self.count_down -= 1
                        print(self.count_down+1)
                    elif self.count_down != -1:
                        self.count_down -= 1
                        self.advances += self.config_json["advance_delay_2"]
                        self.rng.advance(self.config_json["advance_delay_2"])

                if advance_type==0:
                    rand = self.rng.next()
                    print(f"advances:{self.advances}, blink:{hex(rand&0xF)}")
                    heapq.heappush(queue, (wait+1.017, 0))
                else:
                    rand = self.rng.rangefloat(3,12) + 0.285

                    heapq.heappush(queue, (wait+rand, 1))
                    print(f"advances:{self.advances}, interval:{rand}")
            self.timelining = False

    def preview(self):
        """Start preview to be used to correct settings"""
        if not self.previewing:
            self.preview_button['text'] = "停止预览画面"
            self.previewing = True
            self.previewing_thread=threading.Thread(target=self.previewing_work)
            self.previewing_thread.daemon = True
            self.previewing_thread.start()
        else:
            self.preview_button['text'] = "预览画面"
            self.previewing = False

    # pylint: disable=too-many-locals
    # previewing live updates at any setting change
    # many local variables are required to do this
    def previewing_work(self):
        """Thread work to be done for the preview function"""
        last_frame_tk = None
        last_camera = self.config_json["camera"]

        if self.config_json["MonitorWindow"]:
            # pylint: disable=import-outside-toplevel
            # we import here because otherwise it would throw an error on non windows platforms
            from windowcapture import WindowCapture
            video = WindowCapture(self.config_json["WindowPrefix"],self.config_json["crop"])
        else:
            if sys.platform.startswith('linux'): # all Linux
                backend = cv2.CAP_V4L
            else: # MS Windows/macOS/otherwise
                backend = cv2.CAP_ANY # auto-detect via OpenCV
            video = cv2.VideoCapture(self.config_json["camera"],backend)
            video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
            video.set(cv2.CAP_PROP_BUFFERSIZE,1)
            print(f"camera {self.config_json['camera']}")

        while self.previewing:
            if self.config_json["camera"] != last_camera:
                video = cv2.VideoCapture(self.config_json["camera"],backend)
                video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
                video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
                video.set(cv2.CAP_PROP_BUFFERSIZE,1)
                print(f"camera {self.config_json['camera']}")
                last_camera = self.config_json["camera"]

            eye = self.player_eye
            eye_width, eye_height = eye.shape[::-1]
            roi_x, roi_y, roi_w, roi_h = self.config_json["view"]
            if roi_w < eye_width or roi_h < eye_height:
                raise Exception("测眨眼的框的宽度和高度不能小于所选的眼睛图像")
            _, frame = video.read()
            if frame is not None:
                try:
                    roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],
                                       cv2.COLOR_RGB2GRAY)
                except cv2.error as empty_frame:
                    raise Exception("捕获的帧为空" \
                                    "请确保您的摄像头/窗口已正确设置") \
                    from empty_frame
                try:
                    res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
                except cv2.error as bad_location:
                    raise Exception("尝试从摄像头/窗口读取的图像边界之外进行读取，请确保测眨眼的框的位置没有超出边界") \
                    from bad_location
                _, match, _, max_loc = cv2.minMaxLoc(res)

                cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
                if 0.01<match<self.config_json["thresh"]:
                    cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
                else:
                    max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
                    bottom_right = (max_loc[0] + eye_width, max_loc[1] + eye_height)
                    cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
                self.raw_screenshot = frame
                if self.config_json["display_percent"] != 100:
                    _, frame_width, frame_height = frame.shape[::-1]
                    frame = cv2.resize(frame,
                                      (round(frame_width*self.config_json["display_percent"]/100),
                                      round(frame_height*self.config_json["display_percent"]/100)))
                frame_tk = self.cv_image_to_tk(frame)
                self.monitor_tk_buffer = last_frame_tk
                self.monitor_display_buffer['image'] = self.monitor_tk_buffer
                self.monitor_tk = frame_tk
                self.monitor_display['image'] = self.monitor_tk
                last_frame_tk = frame_tk
        self.monitor_tk_buffer = None
        self.monitor_tk = None

    def after_task(self):
        """Task to be run every 100ms, used to update config_json values"""
        self.config_json["view"] = [int(self.pos_x.get()),
                                    int(self.pos_y.get()),
                                    int(self.pos_w.get()),
                                    int(self.pos_h.get())]
        self.config_json["thresh"] = float(self.pos_th.get())
        self.config_json["WindowPrefix"] = self.prefix_input.get()
        self.config_json["white_delay"] = float(self.whi_del.get())
        self.config_json["advance_delay"] = int(self.adv_del.get())
        self.config_json["advance_delay_2"] = int(self.adv_del_2.get())
        self.config_json["npc"] = int(self.npc.get())
        self.config_json["pokemon_npc"] = int(self.pokemon_npc.get())
        self.config_json["timeline_npc"] = int(self.timeline_npc.get())
        self.config_json["MonitorWindow"] = bool(self.monitor_window_var.get())
        self.config_json["camera"] = int(self.camera_index.get())
        self.config_json["display_percent"] = int(self.display_percent.get())
        self.config_json["reident_1_pk_npc"] = bool(self.reident_noisy_check_var.get())
        self.config_json["final_a_press_delay"] = int(self.final_a_press_delay.get())
        self.config_json["timeline_buffer"] = int(self.timeline_buffer.get())
        self.adv['text'] = self.advances
        self.timeline_start = int(self.target_advances.get()) - int(self.timeline_buffer.get())
        self.timeline_start_label['text'] = self.timeline_start
        self.press_a_label['text'] = int(self.target_advances.get()) \
            - int(self.final_a_press_delay.get())
        self.count_down_label['text'] = self.count_down
        self.after(100,self.after_task)

    @staticmethod
    def __signal_handler(_signal, frame):
        """Make sure CTRL+C closes the script"""
        # Ignored parameters
        del _signal, frame
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = PlayerBlinkGUI(master=root)
    app.mainloop()
