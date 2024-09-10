import rngtool
import time
from xorshift import Xorshift

def reidentify():
    t0 = int(input("input state[0] (state 0/1): 0x"),16)
    t1 = int(input("input state[1] (state 0/1): 0x"),16)
    state = [t0 >> 64, t0 & 0xFFFFFFFF, t1 >> 64, t1 & 0xFFFFFFFF]

    observed_blinks, _, offset_time = rngtool.tracking_blink_manual(size = 20, reidentify=True)
    reidentified_rng = rngtool.reidentiy_by_blinks(Xorshift(*state), observed_blinks)
    
    waituntil = time.perf_counter()
    diff = round(waituntil-offset_time)+1
    reidentified_rng.get_next_rand_sequence(diff)

    state = reidentified_rng.get_state()
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))

    advances = 0

    while True:
        advances += 1
        r = reidentified_rng.next()

        waituntil += 1.018

        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)

def expr():
    blinks, intervals, offset_time = rngtool.tracking_blink_manual()
    prng = rngtool.recov(blinks, intervals)

    waituntil = time.perf_counter()
    diff = round(waituntil-offset_time)
    prng.get_next_rand_sequence(diff)

    state = prng.get_state()
    print(hex(state[0]<<32|state[1]), hex(state[2]<<32|state[3]))

    advances = 0

    for _ in range(1000):
        advances += 1
        r = prng.next()
        waituntil += 1.018

        print(f"帧数:{advances}, 眨眼状态:{hex(r&0xF)}")
        
        next_time = waituntil - time.perf_counter() or 0
        time.sleep(next_time)


if __name__ == "__main__":
    if input("查找状态还是重新检测？请输入S或R（查找状态/重新检测）： ") == "R":
        reidentify()
    else:
        expr()