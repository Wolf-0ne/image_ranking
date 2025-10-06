import cv2
import logging

def image_similarity(img1, img2) -> float:

    if img1 is None or img2 is None:
        print("Error: Could not load one or both images.")
        return None

    # Initialize ORB detector
    orb = cv2.ORB_create()

    # Find keypoints and descriptors
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        logging.warning("Could not find enough descriptors in one or both images.")
        return 0

    # Create BFMatcher object
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    # Match descriptors
    matches = bf.match(des1, des2)

    # Sort matches by distance
    matches = sorted(matches, key=lambda x: x.distance)

    # Calculate similarity based on the number of good matches
    # A common approach is to consider a ratio of good matches to the total number of keypoints
    similarity_score = len(matches) / max(len(kp1), len(kp2))

    # Return similarity score between 0 and 1
    return similarity_score
