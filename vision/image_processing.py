import cv2


class ImageProcessor:

    def __init__(self):
        pass

    def gray(self, frame):

        return cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

    def blur(self, gray):

        return cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )

    def edges(self, blur):

        return cv2.Canny(
            blur,
            50,
            150
        )

    def process(self, frame):

        gray = self.gray(frame)

        blur = self.blur(gray)

        edges = self.edges(blur)

        return gray, blur, edges