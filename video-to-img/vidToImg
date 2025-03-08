import cv2
import os

def extract_frames(video_path, base_output_folder="video-to-img", subfolder="extracted_frames", interval=1.0):
    """
    Extract frames from a video at specified intervals and save them in a subfolder.
    
    Parameters:
    - video_path: Path to the input video file
    - base_output_folder: Base folder where subfolder will be created (default: "video_to_image")
    - subfolder: Folder where extracted frames will be saved (default: "extracted_frames")
    - interval: Time interval in seconds between extracted frames (default: 1.0)
    """
    
    # Construct the full output path
    output_folder = os.path.join(base_output_folder, subfolder)
    
    # Create base folder and output folder if they don't exist
    if not os.path.exists(base_output_folder):
        os.makedirs(base_output_folder)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Open the video file
    video = cv2.VideoCapture(video_path)
    
    # Check if video opened successfully
    if not video.isOpened():
        print("Error: Could not open video file")
        return
    
    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)  # Frames per second
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    
    print(f"Video FPS: {fps}")
    print(f"Total frames: {frame_count}")
    print(f"Duration: {duration:.2f} seconds")
    
    # Calculate frame interval in terms of frame numbers
    frame_interval = int(fps * interval)
    
    # Initialize variables
    current_frame = 0
    extracted_count = 0
    
    while True:
        # Set the position to the current frame
        video.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        
        # Read the frame
        success, frame = video.read()
        
        # Break if no more frames
        if not success:
            break
        
        # Save the frame as an image
        output_path = os.path.join(output_folder, f"frame_{extracted_count:04d}.jpg")
        cv2.imwrite(output_path, frame)
        extracted_count += 1
        
        # Move to next frame position based on interval
        current_frame += frame_interval
        
        # Break if we've exceeded total frames
        if current_frame >= frame_count:
            break
    
    # Release the video object
    video.release()
    
    print(f"Extracted {extracted_count} frames")
    print(f"Frames saved in: {output_folder}")

# Example usage with video in same folder
if __name__ == "__main__":
    
    print("Current working directory:", os.getcwd())
    
    # Just use the filename if it's in the same folder as the script
    video_file = "video-to-img\parking.mp4"  # Replace with your actual video filename
    base_dir = "video-to-img"  # Base folder
    output_subdir = "extracted_frames"  # Subfolder for frames
    time_interval = 15  # Extract frame every 15 seconds
    
    extract_frames(video_file, base_dir, output_subdir, time_interval)