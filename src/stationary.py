import rngtool
import cv2
import time
import json
from xorshift import Xorshift
import heapq

config = json.load(open("./configs/config_mt_coronet.json"))

def firstspecify():
    player_eye = cv2.imread(config["image"], cv2.IMREAD_GRAYSCALE)
    if player_eye is None:
        print("眼睛图片路径错误")
        return
    blinks, intervals, offset_time = rngtool.tracking_blink(player_eye, *config["view"], monitor_window=config["MonitorWindow"], window_prefix=config["WindowPrefix"],camera=config["camera"])
    prng = rngtool.recov(blinks, intervals)

    waituntil = time.perf_counter()
    diff = round(waituntil-offset_time)
    prng.get_next_rand_sequence(diff)

    state = prng.get_state()
    print("state(64bit 64bit)")
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))
    print("state(32bit 32bit 32bit 32bit)")
    print(*[hex(s) for s in state])

def reidentify():
    print("input xorshift state(state[0] state[1] state[2] state[3])")
    state = [int(x,0) for x in input().split()]
    player_eye = cv2.imread(config["image"], cv2.IMREAD_GRAYSCALE)
    if player_eye is None:
        print("眼睛图片路径错误")
        return

    observed_blinks, _, offset_time = rngtool.tracking_blink(player_eye, *config["view"], monitor_window=config["MonitorWindow"], window_prefix=config["WindowPrefix"], crop=config["crop"],camera=config["camera"], size=20)
    reidentified_rng = rngtool.reidentiy_by_blinks(Xorshift(*state), observed_blinks)
    if reidentified_rng is None:
        print("无法重新检测当前状态")
        return

    waituntil = time.perf_counter()
    diff = int(-(-(waituntil-offset_time)//1))
    print(diff, waituntil-offset_time)
    reidentified_rng.advance(max(diff,0))

    state = reidentified_rng.get_state()
    print("state(64bit 64bit)")
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))
    print("state(32bit 32bit 32bit 32bit)")
    print(*[hex(s) for s in state])

    #timecounter reset
    advances = 0
    stat_prng = Xorshift(*reidentified_rng.get_state())
    stat_prng.get_next_rand_sequence(2)

    advances = 0
    waituntil = time.perf_counter()
    time.sleep(diff - (waituntil - offset_time))

    while True:
        advances += 1
        r = reidentified_rng.next()
        wild_r = stat_prng.next()

        waituntil += 1.017        
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)
        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")

def stationary_timeline():
    # print("input xorshift state(state[0] state[1] state[2] state[3])")

    # state = [int(x,0) for x in input().split()]
    state = [0x4886CC50, 0x87EC1551, 0xC7F5D167, 0x54F998A8]
    player_eye = cv2.imread(config["image"], cv2.IMREAD_GRAYSCALE)
    if player_eye is None:
        print("眼睛图片路径错误")
        return

    observed_blinks, _, offset_time = rngtool.tracking_blink(player_eye, *config["view"], monitor_window=config["MonitorWindow"], window_prefix=config["WindowPrefix"], crop=config["crop"], threshold=config["thresh"],camera=config["camera"],size=20)
    reidentified_rng = rngtool.reidentiy_by_blinks(Xorshift(*state), observed_blinks)
    if reidentified_rng is None:
        print("无法重新检测当前状态")
        return

    waituntil = time.perf_counter()
    diff = int(-(-(waituntil-offset_time)//1))
    reidentified_rng.advance(max(diff,0))

    state = reidentified_rng.get_state()
    print("state(64bit 64bit)")
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))
    print("state(32bit 32bit 32bit 32bit)")
    print(*[hex(s) for s in state])

    #timecounter reset

    advances = 0
    waituntil = time.perf_counter()
    time.sleep(diff - (waituntil - offset_time))

    for _ in [0]*60:
        advances += 1
        r = reidentified_rng.next()

        waituntil += 1.017
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)
        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")

    #rng blankread
    reidentified_rng.next()
    #whiteout
    time.sleep(2)
    waituntil = time.perf_counter()
    print("进入定点宝可梦所在的的场景")
    queue = []
    heapq.heappush(queue, (waituntil+1.017,0))

    #blink_int = reidentified_rng.range(3.0, 12.0) + 0.285
    blink_int = reidentified_rng.rangefloat(3,12) + 0.285

    heapq.heappush(queue, (waituntil+blink_int,1))
    while queue:
        advances += 1
        w, q = heapq.heappop(queue)
        next_time = w - time.perf_counter() or 0
        if next_time>0:
            time.sleep(next_time)

        if q==0:
            r = reidentified_rng.next()
            print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")
            heapq.heappush(queue, (w+1.017, 0))
        else:
            #blink_int = reidentified_rng.range(3.0, 12.0) + 0.285
            blink_int = reidentified_rng.rangefloat(3,12) + 0.285

            heapq.heappush(queue, (w+blink_int, 1))
            print(f"帧数:{advances}, 时间间隔:{blink_int}")

if __name__ == "__main__":
    #firstspecify()
    #reidentify()
    stationary_timeline()