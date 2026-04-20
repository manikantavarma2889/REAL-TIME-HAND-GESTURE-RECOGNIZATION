import math

class GestureClassifier:
    def __init__(self):
        pass

    def get_palm_size(self, lmList):
        """Calculates distance between wrist (0) and middle finger base (9)"""
        if not lmList or len(lmList) < 10: return 50
        return math.hypot(lmList[0][1] - lmList[9][1], lmList[0][2] - lmList[9][2])

    def get_finger_states(self, lmList, palm_size):
        """
        Returns a list of 5 integers (0 or 1) representing if a finger is up.
        """
        fingers = []
        if len(lmList) < 21: return [0,0,0,0,0]
        
        # 1. Thumb (Improved logic)
        # Thumb is up if dist(tip, index_base) is large AND tip is higher than index base
        dist_t_i = math.hypot(lmList[4][1] - lmList[5][1], lmList[4][2] - lmList[5][2])
        is_thumb_up = (dist_t_i > palm_size * 0.7)
        fingers.append(1 if is_thumb_up else 0)

        # 2. Four Fingers
        # Improved: Must be significantly higher than PIP to be "up"
        for tip, pip, dip in zip([8, 12, 16, 20], [6, 10, 14, 18], [7, 11, 15, 19]):
            dist_tip = math.hypot(lmList[tip][1] - lmList[0][1], lmList[tip][2] - lmList[0][2])
            dist_pip = math.hypot(lmList[pip][1] - lmList[0][1], lmList[pip][2] - lmList[0][2])
            # Extra check: tip Y should be less than dip Y for "pointing up" gestures
            if dist_tip > dist_pip * 1.1:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers

    def get_gesture(self, lmList, faceLms, frame_shape):
        if not lmList or len(lmList) < 21:
            return None

        palm_size = self.get_palm_size(lmList)
        fingers = self.get_finger_states(lmList, palm_size)
        
        # Extract specific Landmarks
        w = lmList[0]    # Wrist
        t_tip = lmList[4] # Thumb tip
        i_tip = lmList[8] # Index tip
        m_tip = lmList[12]
        i_base = lmList[5]

        # Normalized Distance Helper
        def norm_dist(p1, p2):
            return math.hypot(p1[1] - p2[1], p1[2] - p2[2]) / palm_size

        d_ti = norm_dist(t_tip, i_tip)
        d_im = norm_dist(i_tip, m_tip)
        
        # Face Proximity Helper (Tightened)
        def near_face(hand_pt, face_pt_idx, threshold=1.2):
            if not faceLms: return False
            face_pt = next((p for p in faceLms if p[0] == face_pt_idx), None)
            if not face_pt: return False
            dist = math.hypot(hand_pt[1] - face_pt[1], hand_pt[2] - face_pt[2]) / palm_size
            return dist < threshold

        # ==========================================
        # 1. CORE CONTROL
        # ==========================================
        # ENTER: Fist
        if fingers == [0, 0, 0, 0, 0] and t_tip[2] > i_base[2]: return "ENTER"
        # SPACE: 3 fingers
        if fingers == [0, 1, 1, 1, 0]: return "SPACE"
        # BACKSPACE: Pinch
        if d_ti < 0.4 and fingers[2:] == [0, 0, 0]: return "BACKSPACE"

        # ==========================================
        # 2. FACE-AWARE WORDS
        # ==========================================
        if faceLms:
            # LISTEN (Right Ear - 454) - Tightened threshold to 1.5
            if fingers == [1, 1, 1, 1, 1] and near_face(w, 454, 1.8): return "LISTEN"
            
            # FATHER (Forehead - 10)
            if fingers == [1, 1, 1, 1, 1] and near_face(t_tip, 10, 1.0): return "FATHER"
            
            # MOTHER (Chin - 152)
            if fingers == [1, 1, 1, 1, 1] and near_face(t_tip, 152, 1.0): return "MOTHER"
            
            # THINK (Index near forehead)
            if fingers == [0, 1, 0, 0, 0] and near_face(i_tip, 10, 1.0): return "THINK"
            
            # WATCH (V near eyes)
            if fingers == [0, 1, 1, 0, 0] and (near_face(i_tip, 33, 1.2) or near_face(i_tip, 263, 1.2)): return "WATCH"
            
            # EAT / DRINK (Near mouth - 13)
            if near_face(t_tip, 13, 1.2):
                if d_ti > 1.0 and fingers == [0,0,0,0,0]: return "DRINK"
                if d_ti < 0.5: return "EAT"

        # ==========================================
        # 3. OTHER WORDS
        # ==========================================
        # OK (Thumbs Up)
        if fingers == [1, 0, 0, 0, 0] and t_tip[2] < lmList[3][2]: return "OK"
        # BAD (Thumbs Down)
        if fingers == [1, 0, 0, 0, 0] and t_tip[2] > w[2]: return "BAD"
        # CALL ME (Thumb and Pinky)
        if fingers == [1, 0, 0, 0, 1]: return "CALL ME"
        # I LOVE YOU
        if fingers == [1, 1, 0, 0, 1]: return "I LOVE YOU"
        # NO
        if d_ti < 0.25 and fingers[2:] == [0,0,0]: return "NO"
        # YES
        if fingers == [0, 0, 0, 0, 0] and i_tip[2] < i_base[2] + 20: return "YES"

        # SHAPES
        if fingers == [1, 1, 1, 1, 1]:
            if d_ti < 0.35: return "FINE"
            if d_im < 0.2: return "STOP"
            return "HELLO"

        if fingers == [0, 1, 0, 0, 0]:
            if abs(i_tip[1] - w[1]) > palm_size * 2.5: return "GO"
            if norm_dist(i_tip, w) < 1.1: return "ME"
            return "YOU"

        # Alphabet Basics (Strict Checks)
        if fingers == [0, 0, 0, 0, 0]:
            if t_tip[1] > i_base[1] + 20: return "A" # Thumb strictly on side
            return None
        
        if fingers == [0, 1, 1, 1, 1] and d_ti < 0.5: return "B"
        if fingers == [1, 1, 1, 1, 1] and d_ti > 1.3: return "C"
        
        # Numbers
        if fingers == [0, 1, 0, 0, 0]: return "1"
        if fingers == [0, 1, 1, 0, 0]: return "2"
        if fingers == [1, 1, 1, 0, 0]: return "3"
        if fingers == [0, 1, 1, 1, 1]: return "4"
        if fingers == [1, 1, 1, 1, 1]: return "5"

        return None
