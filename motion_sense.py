import cv2
import imutils
import datetime
import requests
import time
from threading import Thread
try:
    import RPi.GPIO as gpio
    import os
    on_pi = True
    os.environ['DISPLAY'] = ':0'
except (ImportError, RuntimeError):
    on_pi = False

size = 500
host = ''
port = 20000
proto = 'http'
endpoint = f'{proto}://{host}:{port}/upload'
headers = {
    'Content-Disposition': '1.jpg',
    #'Content-Type': 'application/x-www-form-urlencoded'
}




def motion_sense_rpi():
    """
    Motion sense for the raspberry pi.
    Meant for optimizing without having to
    try -- catch to show the frame
    :return: None
    """
    video = cv2.VideoCapture(0)
    cc = cv2.VideoWriter_fourcc('M', 'P', '4', 'V')
    first_frame = reset_reference_frame(video, True)
    # set time to be one hour from now
    t = time.time() + (60 * 60)
    print(f'Frame size: {first_frame.shape}')
    # set video writer to be exactly the first frame shape and width
    video_writer = cv2.VideoWriter(f'{datetime.datetime.now().timestamp()}.mp4', cc, 20.0, (first_frame.shape[1], first_frame.shape[0]))

    while True:
        try:
            ret, frame = video.read()
            if not ret:
                print("Video could not be captured in loop")
                continue

            # reset reference every hour
            if time.time() > t:
                print("Time is up! Resetting the reference frame ...")
                first_frame = reset_reference_frame(video, False)

                # set the next time to be one hour until we grab another frame
                t = time.time() + (60 * 60)
            # resize the frame to be smaller
            frame = imutils.resize(frame, size)

            # grayscale it
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # remove noise from frame using GaussianBlur
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # get the absolute different between first frame and captured frame
            frame_delta = cv2.absdiff(gray, first_frame)

            # grab the threshold
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

            # dilate it with 2 iterations
            thresh = cv2.dilate(thresh, None, iterations=2)

            # find contours of the threshold
            cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

            # grab the contours
            cnts = imutils.grab_contours(cnts)

            if len(cnts) == 0:

                # put unoccupied text
                put_text(frame, "Unoccupied")

            else:
                # loop over the contours
                for c in cnts:
                    # compute the bounding box for the contour, draw it on the frame,
                    # and update the text
                    if cv2.contourArea(c) < 1000:
                        continue
                    (x, y, w, h) = cv2.boundingRect(c)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # put occupied text on the frame at hand
                put_text(frame, "Occupied")

            # we only want to write the frame if we found movement
            video_writer.write(frame)

            encode_and_send(frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except KeyboardInterrupt:
            print("SIGINT detected, stopping")
            break


    video.release()
    video_writer.release()
    cv2.destroyAllWindows()


def motion_sense():
    """
    Meant for systems with GUI
    :return: None
    """
    video = cv2.VideoCapture(0)
    cc = cv2.VideoWriter_fourcc('M', 'P', '4', 'V')
    first_frame = reset_reference_frame(video, True)

    # set time to be one hour from now
    t = time.time() + (60 * 60)

    print(f'Frame size: {first_frame.shape}')
    # set video writer to be exactly the first frame shape and width
    video_writer = cv2.VideoWriter('video.mp4', cc, 20.0, (first_frame.shape[1], first_frame.shape[0]))

    while True:
        ret, frame = video.read()
        if not ret:
            print("Video could not be captured in loop")
            continue

        # reset reference every hour
        if time.time() > t:
            print("Time is up! Resetting the reference frame ...")
            first_frame = reset_reference_frame(video, False)

            # set the next time to be one hour until we grab another frame
            t = time.time() + (60 * 60)


        # resize the frame to be smaller
        frame = imutils.resize(frame, size)

        # grayscale it
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # remove noise from frame using GaussianBlur
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # get the absolute different between first frame and captured frame
        frame_delta = cv2.absdiff(gray, first_frame)

        # grab the threshold
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # dilate it with 2 iterations
        thresh = cv2.dilate(thresh, None, iterations=2)

        # find contours of the threshold
        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)

        # grab the contours
        cnts = imutils.grab_contours(cnts)

        if len(cnts) == 0:

            # put unoccupied text
            put_text(frame, "Unoccupied")

        else:
            # loop over the contours
            for c in cnts:
                # compute the bounding box for the contour, draw it on the frame,
                # and update the text
                if cv2.contourArea(c) < 1000:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # put occupied text on the frame at hand
            put_text(frame, "Occupied")

            # we only want to write the frame if we found movement
            video_writer.write(frame)

        # only meant for systems that don't have gui
        try:
            cv2.imshow("Security Feed", frame)
        except Exception:
            pass

        encode_and_send(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


    video.release()
    video_writer.release()
    cv2.destroyAllWindows()


def put_text(frame, text):
    """
    Places the text on the screen
    :param frame: The frame we put the screen on
    :param text: The text to put on the frame
    :return:
    """
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)


def encode_and_send(frame):
    """
    Encodes and sends a frame to the specified global host
    :param frame: The frame to encode & send via the network
    :return:
    """
    def wrapper():
        img_data = cv2.imencode('.jpg', frame)[1].tobytes()
        try:
            requests.post(endpoint, data=img_data, headers=headers)
        except Exception as e:
            #print(e)
            pass
    
    try:
        Thread(target=wrapper, daemon=True).start()
    except Exception:
        pass

def reset_reference_frame(video, first_time=True):
    """
    Resets the first reference frame
    :param video: The video capture object
    :param first_time: A boolean representing if we are getting the first reference
    :return: a grayed frame
    """
    first_frame = None
    times = 50 if first_time else 25
    for i in range(times):
        ret, frame = video.read()

        # resize the frame, convert it to grayscale, and blur it
        frame = imutils.resize(frame, size)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        first_frame = gray

    return first_frame


if __name__ == '__main__':
    if on_pi:
        motion_sense_rpi()
    else:
        motion_sense()
