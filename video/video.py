import cv2
import os
import numpy

# Directory where the painted images are saved.
painted_image_folder = 'progress'

# Directory where the painted images are saved after being labelled with the generation number.
labelled_image_folder = 'labelled'

# Number of generations.
num_generations = 6500
frames = [f'test_{idx}.jpg' for idx in range(num_generations)]

# frames = frames[:500]

im_original_name = 'monaliza.jpg'
im_original = cv2.imread(os.path.join(os.getcwd(), im_original_name), 1)

# Horizontally stack the original and painted images.
for idx in range(len(frames)):
    # Create an empty white image as the background for the original and painted images.
    # Add 50 pixels to the height to make room for the text.
    # Add 20 pixels to the width to make room between the original and painted images.
    background = numpy.zeros([512+50, 512+20+512, 3], dtype=numpy.uint8)
    # Read the painted image from the 'progress' folder.
    im = cv2.imread(os.path.join(os.getcwd(), painted_image_folder, f"test_{idx}.jpg"), 1)
    background[50:, :512] = im_original
    background[50:, 532:] = im

    # The text represents the generation number.
    text = f'Generation {idx}'
    # Font family.
    fontFace = cv2.FONT_HERSHEY_SIMPLEX
    # Font scale. Make it larger than normal.
    fontScale = 1.7
    # Text color.
    color=(255, 255, 255)
    # Make the text bold.
    thickness=5

    # Get the text size. Then use the size to center the text horizontally.
    text_width, text_height = cv2.getTextSize(text=text, 
                                              fontFace=fontFace, 
                                              fontScale=fontScale, 
                                              thickness=thickness)[0]

    # Horizontally center the text at the top.
    CenterCoordinates = (int(background.shape[1] / 2) - int(text_width / 2),
                         # int(background.shape[0] / 2) + int(text_height / 2)
                         40
                         )

    cv2.putText(img=background, 
                text=text, 
                org=CenterCoordinates, 
                fontFace=fontFace, 
                fontScale=fontScale, 
                color=color, 
                thickness=thickness, 
                lineType=cv2.LINE_AA)
    # Save the labeled image in the 'labelled' folder.
    cv2.imwrite(os.path.join(os.getcwd(), labelled_image_folder, f"test_{idx}.jpg"), background)

# Number of frames per second.
fps=50

# The video dimensions.
video_dim = (background.shape[1], background.shape[0])
# write to MP4 file
# fourcc = cv2.VideoWriter_fourcc(*'XVID')
# fourcc =  cv2.VideoWriter_fourcc(*"mp4v")
# fourcc = cv2.VideoWriter_fourcc(*'MJPG')
fourcc = cv2.CAP_GSTREAMER
vidwriter = cv2.VideoWriter(filename="output.mp4", 
                            fourcc=fourcc, 
                            fps=fps, 
                            frameSize=video_dim)
# Write the frames into the video.
for frame in frames:
    # Read the labeled frame.
    img_frame = cv2.imread(os.path.join(os.getcwd(), labelled_image_folder, frame), 
                           cv2.IMREAD_COLOR)
    vidwriter.write(img_frame)
vidwriter.release()
