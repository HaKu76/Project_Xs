import rngtool
import cv2
import time
import json
from xorshift import Xorshift

config = json.load(open("./configs/config_wild.json"))

def expr():
    player_eye = cv2.imread(config["image"], cv2.IMREAD_GRAYSCALE)
    if player_eye is None:
        print("眼睛图片路径错误")
        return
    blinks, intervals, offset_time = rngtool.tracking_blink(player_eye, *config["view"], monitor_window=config["MonitorWindow"], window_prefix=config["WindowPrefix"], crop=config["crop"],camera=config["camera"])
    prng = rngtool.recov(blinks, intervals)

    waituntil = time.perf_counter()
    diff = round(waituntil-offset_time)
    prng.get_next_rand_sequence(diff)

    state = prng.get_state()
    print("state(64bit 64bit)")
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))
    print("state(32bit 32bit 32bit 32bit)")
    print(*[hex(s) for s in state])

    advances = 0
    for _ in range(1000):
        advances += 1
        r = prng.next()
        waituntil += 1.018

        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)

def reidentify():
    state = [int(x,0) for x in config["reidentify"].split()]
    print("base state:", [hex(x) for x in state])

    player_eye = cv2.imread(config["image"], cv2.IMREAD_GRAYSCALE)
    if player_eye is None:
        print("眼睛图片路径错误")
        return

    observed_blinks, _, offset_time = rngtool.tracking_blink(player_eye, *config["view"], monitor_window=config["MonitorWindow"], window_prefix=config["WindowPrefix"], crop=config["crop"],camera=config["camera"], size=20)
    reidentified_rng = rngtool.reidentiy_by_blinks(Xorshift(*state), observed_blinks)
    
    waituntil = time.perf_counter()
    diff = int(-(-(waituntil-offset_time)//1))
    reidentified_rng.advance(max(diff,0))

    state = reidentified_rng.get_state()
    print("state(64bit 64bit)")
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))
    print("state(32bit 32bit 32bit 32bit)")
    print(*[hex(s) for s in state])

    advances = 0

    while True:
        advances += 1
        r = reidentified_rng.next()

        waituntil += 1.018

        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)

if __name__ == "__main__":
    if config["reidentify"] != "":
        reidentify()
    else:
        expr()