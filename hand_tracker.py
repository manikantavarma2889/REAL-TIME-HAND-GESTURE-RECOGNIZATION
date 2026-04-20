import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, mode=False, detectionCon=0.5, trackCon=0.5):
        self.mpHolistic = mp.solutions.holistic
        self.holistic = self.mpHolistic.Holistic(
            static_image_mode=mode,
            min_detection_confidence=detectionCon,
            min_tracking_confidence=trackCon
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.mpHands = mp.solutions.hands # Still need connections for drawing

    def findFullLandmarks(self, img):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.holistic.process(imgRGB)
        
        # Draw only hand landmarks as requested
        if self.results.left_hand_landmarks:
            self.mpDraw.draw_landmarks(img, self.results.left_hand_landmarks, self.mpHands.HAND_CONNECTIONS)
        if self.results.right_hand_landmarks:
            self.mpDraw.draw_landmarks(img, self.results.right_hand_landmarks, self.mpHands.HAND_CONNECTIONS)
            
        return img

    def getPositions(self, img):
        """
        Returns (hand_lmList, face_lmList)
        hand_lmList: [[id, x, y], ...] for the primary hand found
        face_lmList: [[id, x, y], ...] for key face points
        """
        hand_lmList = []
        face_lmList = []
        
        # Get one hand for logic (prefer right hand as primary)
        h_lms = self.results.right_hand_landmarks or self.results.left_hand_landmarks
        
        if h_lms:
            for id, lm in enumerate(h_lms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                hand_lmList.append([id, cx, cy])

        # Get key face landmarks
        # 10: Forehead, 152: Chin, 33: L-Eye, 263: R-Eye, 234: L-Ear, 454: R-Ear
        if self.results.face_landmarks:
            h, w, c = img.shape
            for id in [10, 152, 33, 263, 234, 454, 13]: # 13 is mouth
                lm = self.results.face_landmarks.landmark[id]
                face_lmList.append([id, int(lm.x * w), int(lm.y * h)])
                
        return hand_lmList, face_lmList
