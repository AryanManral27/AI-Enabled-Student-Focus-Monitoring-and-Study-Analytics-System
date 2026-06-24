import cv2
import math
import time
import numpy as np
from datetime import datetime
import os

class FocusDetectorLogic:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.session_data = self.reset_session_data()
        
        # These will be approximated from bounding boxes
        self.LEFT_EYE_INDICES = list(range(6)) 
        self.RIGHT_EYE_INDICES = list(range(6))
        self.EAR_THRESHOLD = 0.18
        self.FOCUS_FRAME_THRESHOLD = 2

    def reset_session_data(self):
        return {
            'total_study_time': 0,
            'total_focused_time': 0,
            'session_start_time': time.time(),
            'last_frame_time': time.time(),
            'is_focused': False,
            'focused_frames': 0,
            'unfocused_frames': 0,
            'avg_ear': 0.0,
            'frame_count': 0,
            'ear_history': [],
            'confidence_history': [],
            'ear_threshold': 0.18,
            'current_tier': self.get_reward_tier(0),
            'current_reward': self.get_reward(0),
        }

    def calculate_ear(self, eye_rect):
        if eye_rect is None:
            return 0.0
        
        x, y, w, h = eye_rect
        
        # Approximate vertical eye landmarks (p2, p3, p5, p6)
        # and horizontal eye landmarks (p1, p4)
        # For simplicity, we assume the eye is an ellipse within the bounding box
        # and use fixed ratios to estimate landmark positions.
        
        # Vertical points
        p2_y = y + h * 0.2
        p3_y = y + h * 0.8
        p5_y = y + h * 0.2
        p6_y = y + h * 0.8
        
        # Horizontal points
        p1_x = x + w * 0.1
        p4_x = x + w * 0.9
        
        # Simplified distances for EAR calculation
        A = math.sqrt(0 + (p2_y - p6_y)**2) # Vertical distance
        B = math.sqrt(0 + (p3_y - p5_y)**2) # Vertical distance
        C = math.sqrt((p1_x - p4_x)**2 + 0) # Horizontal distance
        
        try:
            ear = (A + B) / (2.0 * C)
            return ear
        except ZeroDivisionError:
            return 0.0

    def is_looking_at_camera(self, face_rect, frame_width):
        if face_rect is None:
            return False
        
        x, _, w, _ = face_rect
        
        face_center_x = x + w / 2
        frame_center_x = frame_width / 2
        
        # Define a tolerance for how far the face center can be from the frame center
        # For simplicity, let's say 10% of the frame width
        gaze_tolerance = frame_width * 0.10
        
        return abs(face_center_x - frame_center_x) < gaze_tolerance

    def detect_focus(self, left_ear, right_ear, avg_ear, gaze_direction):
        criteria = {
            'eyes_open_normal': avg_ear > self.EAR_THRESHOLD,
            'eyes_symmetrical': abs(left_ear - right_ear) < 0.08,
            'gaze_forward': gaze_direction,
        }
        
        confidence = 0
        if criteria['eyes_open_normal']: confidence += 2
        if criteria['eyes_symmetrical']: confidence += 1
        if criteria['gaze_forward']: confidence += 2
        
        is_focused_new = confidence >= 3
        
        if is_focused_new:
            self.session_data['focused_frames'] += 1
            self.session_data['unfocused_frames'] = 0
            if self.session_data['focused_frames'] >= self.FOCUS_FRAME_THRESHOLD:
                return True
        else:
            self.session_data['unfocused_frames'] += 1
            self.session_data['focused_frames'] = 0
            if self.session_data['unfocused_frames'] >= self.FOCUS_FRAME_THRESHOLD:
                return False
        
        return self.session_data['is_focused']

    def process_frame(self, frame, delta_time):
        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 5)
        
        is_focused = False
        avg_ear = 0.0
        gaze_direction = False
        face_rect = None
        left_ear = 0.0
        right_ear = 0.0
        left_eye_rect = None
        right_eye_rect = None

        if len(faces) > 0:
            # Assuming only one face for simplicity, take the largest one
            (x, y, w, h) = max(faces, key=lambda rect: rect[2] * rect[3])
            face_rect = (x, y, w, h)
            
            # Draw face bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            roi_gray = gray_frame[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            # Assuming two eyes for EAR calculation
            if len(eyes) == 2:
                eye1_x, eye1_y, eye1_w, eye1_h = eyes[0]
                eye2_x, eye2_y, eye2_w, eye2_h = eyes[1]
                
                # Determine which eye is left and which is right based on x-coordinate
                if eye1_x < eye2_x:
                    left_eye_rect = (x + eye1_x, y + eye1_y, eye1_w, eye1_h)
                    right_eye_rect = (x + eye2_x, y + eye2_y, eye2_w, eye2_h)
                else:
                    left_eye_rect = (x + eye2_x, y + eye2_y, eye2_w, eye2_h)
                    right_eye_rect = (x + eye1_x, y + eye1_y, eye1_w, eye1_h)
                
                # Draw eye bounding boxes
                cv2.rectangle(frame, (left_eye_rect[0], left_eye_rect[1]), 
                              (left_eye_rect[0]+left_eye_rect[2], left_eye_rect[1]+left_eye_rect[3]), (0, 255, 0), 2)
                cv2.rectangle(frame, (right_eye_rect[0], right_eye_rect[1]), 
                              (right_eye_rect[0]+right_eye_rect[2], right_eye_rect[1]+right_eye_rect[3]), (0, 255, 0), 2)

                left_ear = self.calculate_ear(left_eye_rect)
                right_ear = self.calculate_ear(right_eye_rect)
                
                if left_ear > 0 and right_ear > 0:
                    avg_ear = (left_ear + right_ear) / 2.0
                elif left_ear > 0:
                    avg_ear = left_ear
                elif right_ear > 0:
                    avg_ear = right_ear
                
                if avg_ear > 0:
                    self.session_data['ear_history'].append(avg_ear)
                    if len(self.session_data['ear_history']) > 60:
                        self.session_data['ear_history'].pop(0)

            gaze_direction = self.is_looking_at_camera(face_rect, width)
            is_focused = self.detect_focus(left_ear, right_ear, avg_ear, gaze_direction)
                
        self.session_data['avg_ear'] = avg_ear
        self.session_data['is_focused'] = is_focused
        self.session_data['total_study_time'] += delta_time
        
        if self.session_data['total_study_time'] > 120:
            self.session_data['total_study_time'] = 120
        
        # Returning None for results as it's no longer MediaPipe-specific
        return frame, gaze_direction, None

    def clean_reward_text(self, reward):
        clean = reward.replace("🏆", "").replace("🚌", "").replace("🔬", "")
        clean = clean.replace("🎪", "").replace("🏅", "").replace("🎁", "")
        clean = clean.replace("📜", "").replace("📚", "").strip()
        return clean[:50] + "..." if len(clean) > 50 else clean

    def get_reward_tier(self, focused_minutes):
        if focused_minutes >= 1.8:
            return "PLATINUM ⭐"
        elif focused_minutes >= 1.4:
            return "GOLD 🥇"
        elif focused_minutes >= 1.0:
            return "SILVER 🥈"
        elif focused_minutes >= 0.8:
            return "BRONZE 🥉"
        else:
            return "NO TIER"

    def get_reward(self, focused_minutes):
        if focused_minutes >= 2.0:
            return "Certificates of Achievement for 'Most Focused Learner'"
        elif focused_minutes >= 1.8:
            return "Field Trips / Industrial Visits for top achievers"
        elif focused_minutes >= 1.6:
            return "Early Access to Workshops / Labs"
        elif focused_minutes >= 1.4:
            return "Priority in College Events"
        elif focused_minutes >= 1.2:
            return "Special Badges / Pins for campus events"
        elif focused_minutes >= 1.0:
            return "Gift Vouchers / Coupons for bookstores"
        elif focused_minutes >= 0.8:
            return "Appreciation Certificate"
        else:
            return "No reward yet. Focus for at least 0.8 minutes!"

    def get_session_summary(self):
        study_minutes = self.session_data['total_study_time'] / 60.0
        focus_minutes = self.session_data['total_focused_time'] / 60.0
        focus_rate = (focus_minutes / study_minutes * 100) if study_minutes > 0 else 0
        
        current_tier = self.get_reward_tier(focus_minutes)
        current_reward = self.get_reward(focus_minutes)

        summary = f"""🎓 SESSION SUMMARY
📚 Total Study Time: {study_minutes:.1f}/2.0 minutes ({(study_minutes/2.0)*100:.1f}%)
👀 Total Focused Time: {focus_minutes:.1f}/2.0 minutes ({(focus_minutes/2.0)*100:.1f}%)
📊 Focus Rate: {focus_rate:.1f}% of study time
🏆 Final Tier: {current_tier}
🎁 Final Reward: {current_reward}

{"🌟 INCREDIBLE! Maximum focus achieved!" if focus_minutes >= 2.0 else
 "🌟 AMAZING! Platinum tier achieved!" if focus_minutes >= 1.8 else
 "🥇 GREAT JOB! Gold tier achieved!" if focus_minutes >= 1.4 else
 "🥈 WELL DONE! Silver tier achieved!" if focus_minutes >= 1.0 else
 "🥉 GOOD START! Bronze tier achieved!" if focus_minutes >= 0.8 else
 "💪 Keep practicing! Try to focus for at least 0.8 minutes next time."}
"""
        return summary