# Project_Xs

## 关于
本项目汉化由 白白不是公主/Hakuhiro 一人完成 包含修改、打包、测试

本软件用于宝可梦BDSP珍珠钻石复刻（晶灿钻石／明亮珍珠）的乱数操作

打包成可执行文件采用了upx进行优化

运行前请确保包含的文件夹images和configs存在，双击打开exe文件即可运行

有问题请前往本人博客haku76.github.io寻找联系方式，或者b站搜索相关教程联系到我

# 以下是说明文档
## What's this?
Project_Xs is a program that aims recover the internal state of Pokemon BDSPs Xorshift random number generator via observation of player/pokemon random blinks.

## Environment
 - Git 2.34.1 (Latest version)
 - Python 3.9.6 (Probably works with Python 3.7 and above but has not been tested)

## How to run
Run the following commands to download the repository and run the gui script.
```
git clone https://github.com/Lincoln-LM/Project_Xs.git # Clone the repo with git
cd ./Project_Xs # Enter the folder for the repository
pip install -r requirements.txt # Install the pip requirements
python ./src/player_blink_gui.py # Run the gui script
```

## GUI Info
Progress - The progress counter (defaults to 0/0) displays how many blinks have been logged, and how many need to be logged

S[0-3] - The S[0-3] box displays the state split into 4 seeds for use with chatot

S[0-1] - The S[0-1] box displays the state split into 2 seeds for use with pokefinder

Advances - The Advances display shows the amount of advances since the state displayed above

Timer - The Timer display shows the amount of advances until you need to press A for a timeline

X to advance - The X to advance input controls the amount of advances that will happen when you click the button below

Config - The selection in the top center of the gui controls what config is selected, the "+" to the right of it creates a new config

Eye Display - The eye image below the config selection displays the selected eye image (what the program is searching for)

Camera - The Camera selection controls what camera index the program pulls video from when "Monitor Window" is unchecked

Monitor Window (WINDOWS ONLY) - The monitor window input controls the name of the window that the program pulls video from when "Monitor Window" is checked

Display - The display in the very center displays what the program currently sees, it is only active when monitoring blinks/reidentifying/previewing/tidsid

Preview - The preview button activates the display and has it live update when you change your settings, this displays what the program will see when monitoring blinks in order to make sure your settings are correct

Monitor Blinks - The monitor blinks button will record 40 player blinks and use it to determine your current state, and then begin tracking advances since then

Reidentify - The reidentify button will record 20 player blinks and use it to find the amount of advances since the seeds entered in "S[0-3]", and then begin tracking advances since then

TID/SID - The tid/sid button will record 64 munchlax blinks and use it to determine your current state during the intro sequence, and then begin tracking advances since then

Stop Tracking - The stop tracking button will stop the advances counter from incrementing

Timeline - The timeline button is used for RNGs that require a timeline, such as legendaries or the starters, it will start the countdown from 10, and if advance delay 2 != 0, it will do a second countdown afterwards

+1 on menu close - The +1 on menu close button will account for the +1 that happens when you close the text box before your RNG

X/Y/W/H - These settings control the position and size of the area in the image that will be searched for the eye

Threshold - Threshold controls how sure the program needs to be that an eye is visible, decrease this if you are having difficulty detecting the eye

Time Delay - Time Delay controls the amount of time that the game pauses after the first timeline A press (the time it takes to enter a room for legends, time it takes to get to next text box for starters)

Advance Delay - Advance Delay controls the amount of advances that happen after the first A press, (random legendaries have this 1 higher than their non random counterparts)

Advance Delay 2 - Advance Delay 2 controls the amount of advances that happen after the second A press (currently only used for starters)

NPCs - NPCs controls the amount of NPCs that are active while you are reidentifying your state (the amount of non player characters that are currently rolling for blinks, 1 your rival at the lake)

NPCs during Timeline - NPCs during Timeline controls the amount of non player characters that roll for blinks during the timeline (-1 if player blinks are not rolled for, like with starters, 0 if there are no npcs)

Pokemon NPCs - Pokemon NPCs controls the amount of pokemon that are rolling for blinks (1 for legendaries as their models blinks, 2 for starters due to the two starly)

Select Eye - The Select Eye button is used to change the image that the program searches for when looking for blinks (this should be a closely wrapped image of the player/pokemons eye)

Save Config - The Save Config button is used to save the current settings to the config file that is selected

# Original Readme
## なにこれ
ゴンベの瞬きから色々するプログラムです.
が, β版のため恐らくそのままだとまともに動きません. 色々改変してください.

## 実行環境
Python 3.9.6 (恐らくPython 3.7≧なら動きます)

OpenCV 4.5.4

## 実行方法
以下のコマンドの意味が全部分からない場合は諦めてください

一部分からない場合はgoogle先生に聞いてください
```
git clone https://github.com/Lincoln-LM/Project_Xs.git
cd ./Project_Xs
pip install -r requirements.txt
python ./src/player_blink_gui.py
```
