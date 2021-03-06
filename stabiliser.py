import logging
import time
from statistics import mean

import numpy as np
import cv2

from utils import Features, Modes


class Stabiliser:
    """Video stabiliser."""

    def __init__(self, mode: str, logger: logging.Logger, smoothing_radius: int, features: str):
        self.mode = mode
        self.logger = logger
        self.radius = smoothing_radius
        self.cap: cv2.VideoCapture
        self.out: cv2.VideoWriter
        self.features = features
        self.feature_detection_times = []
        self.feature_detection_kp_counts = []

    def __del__(self):
        self.logger.info(f'Average feature detection time: {mean(self.feature_detection_times)}')
        self.logger.info(f'Average number of features: {mean(self.feature_detection_kp_counts)}')
        cv2.destroyAllWindows()
        self.cap.release()
        self.out.release()

    def moving_average(self, curve):
        window_size = 2 * self.radius + 1
        # Define the filter
        f = np.ones(window_size) / window_size
        # Add padding to the boundaries
        curve_pad = np.lib.pad(curve, (self.radius, self.radius), 'edge')
        # Apply convolution
        curve_smoothed = np.convolve(curve_pad, f, mode='same')
        # Remove padding
        curve_smoothed = curve_smoothed[self.radius:-self.radius]
        # return smoothed curve
        return curve_smoothed

    def smooth(self, trajectory):
        smoothed_trajectory = np.copy(trajectory)
        # Filter the x, y and angle curves
        for i in range(3):
            smoothed_trajectory[:, i] = self.moving_average(trajectory[:, i])
        return smoothed_trajectory

    @staticmethod
    def fix_border(frame):
        s = frame.shape
        # Scale the image 4% without moving the center
        T = cv2.getRotationMatrix2D((s[1] / 2, s[0] / 2), 0, 1.04)
        frame = cv2.warpAffine(frame, T, (s[1], s[0]))
        return frame

    @staticmethod
    def convert_cv_kps_to_np(kps):
        """Converts tuples of KeyPoints to ndarrays."""
        key_points = []
        for kp in kps:
            key_points.append([[int(kp.pt[0]), int(kp.pt[1])]])
        return np.array(key_points).astype('float32')

    def get_features(self, gray):
        start = time.time()

        if self.features == Features.GOOD_FEATURES:
            kps = cv2.goodFeaturesToTrack(
                gray, maxCorners=200, qualityLevel=0.01, minDistance=30, blockSize=3)

        elif self.features == Features.SURF:
            # todo: I had trouble implementing it, a game not worth the candle probably
            raise NotImplementedError

        elif self.features == Features.SIFT:
            sift = cv2.SIFT_create()
            kps = sift.detect(gray, None)

        elif self.features == Features.ORB:
            orb = cv2.ORB_create()
            kps, _ = orb.detectAndCompute(gray, None)

        elif self.features == Features.AKAZE:
            akaze = cv2.AKAZE_create()
            kps, _ = akaze.detectAndCompute(gray, None)

        elif self.features == Features.KAZE:
            akaze = cv2.KAZE_create()
            kps, _ = akaze.detectAndCompute(gray, None)

        elif self.features == Features.FAST:
            fast = cv2.FastFeatureDetector_create()
            kps = fast.detect(gray, None)

        elif self.features == Features.MSER:
            mser = cv2.MSER_create()
            kps = mser.detect(gray, None)

        elif self.features == Features.BRISK:
            mser = cv2.BRISK_create()
            kps = mser.detect(gray, None)

        end = time.time()
        elapsed_time = end - start
        self.logger.info(f'Detecting features took {elapsed_time} seconds.')
        self.feature_detection_times.append(elapsed_time)
        self.feature_detection_kp_counts.append(len(kps))

        return kps if self.features == Features.GOOD_FEATURES else self.convert_cv_kps_to_np(kps)

    def extract_sift_features(self, img1, img2):
        # Initiate SIFT detector
        sift = cv2.SIFT_create()

        # find the keypoints and descriptors with SIFT
        kp1, des1 = sift.detectAndCompute(img1, None)

        kp2, des2 = sift.detectAndCompute(img2, None)

        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)

        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # store all the good matches as per Lowe's ratio test.
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)
        return good, kp1, kp2

    def stabilise(self, input_path: str, output_path: str):
        self.cap = cv2.VideoCapture(input_path)

        # Get frame count
        n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Get width and height of video stream
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Get frames per second (fps)
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        # Define the codec for output video
        fourcc = cv2.VideoWriter_fourcc(*'MP4V')

        # Set up output video
        self.out = cv2.VideoWriter(output_path, fourcc, fps, (2 * w, h))

        # Read first frame
        _, prev = self.cap.read()

        # Convert frame to grayscale
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)

        # Pre-define transformation-store array
        transforms = np.zeros((n_frames - 1, 3), np.float32)

        for i in range(n_frames - 2):
            # Read next frame
            success, curr = self.cap.read()
            if not success:
                break

            # Convert to grayscale
            curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)

            if self.mode == Modes.HOMOGRAPHY:
                good, kp1, kp2 = self.extract_sift_features(prev_gray, curr_gray)

                prev_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                curr_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

                m, mask = cv2.findHomography(prev_pts, curr_pts, cv2.RANSAC, 5.0)
            elif self.mode == Modes.OPTICAL_FLOW:
                # Detect feature points in previous frame
                prev_pts = self.get_features(prev_gray)
                # Calculate optical flow (i.e. track feature points)
                curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None)

            # Sanity check
            assert prev_pts.shape == curr_pts.shape

            if self.mode == Modes.OPTICAL_FLOW:
                # Filter only valid points
                idx = np.where(status == 1)[0]
                prev_pts = prev_pts[idx]
                curr_pts = curr_pts[idx]

                # Find transformation matrix
                m = cv2.estimateRigidTransform(prev_pts, curr_pts, fullAffine=False)

            # Extract traslation
            dx = m[0, 2]
            dy = m[1, 2]

            # Extract rotation angle
            da = np.arctan2(m[1, 0], m[0, 0])

            # Store transformation
            transforms[i] = [dx, dy, da]

            # Move to next frame
            prev_gray = curr_gray

            self.logger.info(f'Frame: {i}/{n_frames} -  Tracked points : {len(prev_pts)}')

        # Compute trajectory using cumulative sum of transformations
        trajectory = np.cumsum(transforms, axis=0)

        # Create variable to store smoothed trajectory
        smoothed_trajectory = self.smooth(trajectory)

        # Calculate difference in smoothed_trajectory and trajectory
        difference = smoothed_trajectory - trajectory

        # Calculate newer transformation array
        transforms_smooth = transforms + difference

        # Reset stream to first frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Write n_frames-1 transformed frames
        for i in range(n_frames - 2):
            # Read next frame
            success, frame = self.cap.read()
            if not success:
                break

            # Extract transformations from the new transformation array
            dx = transforms_smooth[i, 0]
            dy = transforms_smooth[i, 1]
            da = transforms_smooth[i, 2]

            # Reconstruct transformation matrix accordingly to new values
            m = np.zeros((2, 3), np.float32)
            m[0, 0] = np.cos(da)
            m[0, 1] = -np.sin(da)
            m[1, 0] = np.sin(da)
            m[1, 1] = np.cos(da)
            m[0, 2] = dx
            m[1, 2] = dy

            # Apply affine wrapping to the given frame
            frame_stabilized = cv2.warpAffine(frame, m, (w, h))

            # Fix border artifacts
            frame_stabilized = self.fix_border(frame_stabilized)

            # Write the frame to the file
            frame_out = cv2.hconcat([frame, frame_stabilized])

            # If the image is too big, resize it.
            if frame_out.shape[1] > 1920:
                frame_out = cv2.resize(frame_out, (frame_out.shape[1] / 2, frame_out.shape[0] / 2))

            cv2.imshow("Before (left) and After (right)", frame_out)
            cv2.waitKey(10)
            self.out.write(frame_out)
