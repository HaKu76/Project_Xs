"""Module to capture frames from a open window"""
import numpy as np
try:
    import win32gui
    import win32ui
    import win32con
except ImportError as failed_import:
    raise Exception("无法导入包win32, " \
                    "如果您不是windows系统，捕捉窗口必须未选中，" \
                    "否则，请确保已经正确安装了win32软件包") \
                        from failed_import

# pylint: disable=too-many-instance-attributes
class WindowCapture:
    """Class to monitor a window"""
    def __init__(self, partial_window_title, crop):
        # set up variables
        self.width = 0
        self.height = 0
        self.hwnd = None
        self.cropped_x = 0
        self.cropped_y = 0
        self.offset_x = 0
        self.offset_y = 0

        # a string contained in the window title,
        # used to find windows who's name is not constant
        self.partial_window_title = partial_window_title
        # find the handle for the window we want to capture
        hwnds = []
        win32gui.EnumWindows(self.win_enum_handler, hwnds)
        if len(hwnds) == 0:
            raise Exception('没找到对应窗口，请检查窗口名是否正确输入')
        self.hwnd = hwnds[0]

        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.width = window_rect[2] - window_rect[0]
        self.height = window_rect[3] - window_rect[1]

        # account for the window border and titlebar and cut them off
        border_pixels = 8
        titlebar_pixels = 31
        self.width = self.width - (border_pixels * 2)
        self.height = self.height - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels
        if crop is not None and crop != [0,0,0,0]:
            self.cropped_x,self.cropped_y,self.width,self.height = crop

        # set the cropped coordinates offset
        # so we can translate screenshot images into actual screen positions
        self.offset_x = window_rect[0] + self.cropped_x
        self.offset_y = window_rect[1] + self.cropped_y

    def win_enum_handler(self, hwnd, ctx):
        """Handler for finding the target window"""
        # check if window is not minimized
        if win32gui.IsWindowVisible(hwnd):
            # check if our partial title is contained in the actual title
            if self.partial_window_title in win32gui.GetWindowText(hwnd):
                # add to list
                ctx.append(hwnd)

    def read(self):
        """Send a screenshot of the window to cv2"""
        # get the window image data
        window_dc = win32gui.GetWindowDC(self.hwnd)
        dc_object = win32ui.CreateDCFromHandle(window_dc)
        compatible_dc = dc_object.CreateCompatibleDC()
        data_bitmap = win32ui.CreateBitmap()
        try:
            data_bitmap.CreateCompatibleBitmap(dc_object, self.width, self.height)
        except win32ui.error as failed_read:
            raise Exception("无法拉取目标窗口，" \
                            "请确保没有其他软件或程序正在调用访问该窗口" \
                            "（在捕捉眨眼之前先停止预览）") \
                                from failed_read
        compatible_dc.SelectObject(data_bitmap)
        compatible_dc.BitBlt((0, 0),
                             (self.width, self.height),
                             dc_object,
                             (self.cropped_x, self.cropped_y),
                             win32con.SRCCOPY)

        # convert the raw data into a format opencv can read
        signed_ints_array = data_bitmap.GetBitmapBits(True)
        img = np.fromstring(signed_ints_array, dtype='uint8')
        img.shape = (self.height, self.width, 4)

        # free resources
        dc_object.DeleteDC()
        compatible_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, window_dc)
        win32gui.DeleteObject(data_bitmap.GetHandle())

        # drop the alpha channel, to avoid throwing an error
        img = img[...,:3]

        # make image C_CONTIGUOUS to avoid errors
        # https://github.com/opencv/opencv/issues/14866#issuecomment-580207109
        img = np.ascontiguousarray(img)

        return True,img

    def get_screen_position(self, pos):
        """Translate a pixel position to position on screen"""
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)

    def release(self):
        """Empty function for compatibility with cv2.VideoCapture"""
