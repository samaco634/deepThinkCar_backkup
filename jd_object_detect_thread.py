import threading

import sys

import cv2
from tflite_support.task import core
from tflite_support.task import processor
from tflite_support.task import vision

_MARGIN = 10  # pixels
_ROW_SIZE = 10  # pixels
_FONT_SIZE = 1
_FONT_THICKNESS = 1
_TEXT_COLOR = (0, 0, 255)  # red

stop_width, stop_height = 60, 60

# Define the thread that will continuously pull frames from the camera
class JdObejctDetectThread(threading.Thread):
    def __init__(self, camera, name='jd-object-detect-thread', model = './models/efficientdet_lite0.tflite', frameWidth = 320, frameHeight = 240, numThreads = 4, enableEdgeTPU = False ):
        self.camera = camera
        self.last_frame = None
        super(JdObejctDetectThread, self).__init__(name=name)
        self.running = True
        self.start()
        self.ret = False
        self.stopSign = False
        self.model = model
        self.frameWidth = frameWidth
        self.frameHeight = frameHeight
        self.numThreads = numThreads
        self.enableEdgeTPU = enableEdgeTPU
        
    def run(self):
        while self.running:
            self.ret, self.last_frame = self.camera.read()
                        
            # Visualization parameters
            row_size = 20  # pixels
            left_margin = 24  # pixels 
            text_color = (0, 0, 255)  # red
            font_size = 1
            font_thickness = 1
            fps_avg_frame_count = 10
            
            # Initialize the object detection model          
            base_options = core.BaseOptions(
                  file_name=self.model, use_coral=self.enableEdgeTPU, num_threads=self.numThreads)
            detection_options = processor.DetectionOptions(category_name_allowlist=['stop sign'],
              max_results=3, score_threshold=0.3)
            options = vision.ObjectDetectorOptions(
              base_options=base_options, detection_options=detection_options)
            detector = vision.ObjectDetector.create_from_options(options)
            
            # Continuously capture images from the camera and run inference
            if not self.ret:
              sys.exit(
                  'ERROR: Unable to read from webcam. Please verify your webcam settings.'
              )

            # Convert the image from BGR to RGB as required by the TFLite model.
            rgb_image = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
            
            # Create a TensorImage object from the RGB image.
            input_tensor = vision.TensorImage.create_from_array(rgb_image)
            
            # Run object detection estimation using the model.
            detection_result = detector.detect(input_tensor)
            
            if len(detection_result.detections) > 0 : 
                # Draw keypoints and edges on input image
                for detection in detection_result.detections:
                    # Draw bounding_box
                    bbox = detection.bounding_box
                    start_point = bbox.origin_x, bbox.origin_y
                    end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
                    #print(f"width : {bbox.width}, height : {bbox.height}")
                    cv2.rectangle(self.last_frame, start_point, end_point, _TEXT_COLOR, 3)
                    
                    # Draw label and score
                    category = detection.categories[0]
                    category_name = category.category_name
                    probability = round(category.score, 2)
                        
                    result_text = category_name + ' (' + str(probability) + ')'
                    
                    if ( category_name == 'stop sign'):
                        if(bbox.width > stop_width or bbox.height > stop_height):
                            print( bbox.width , ", ",  bbox.height)
                            self.stopSign = True
                        
                    text_location = (_MARGIN + bbox.origin_x,
                                     _MARGIN + _ROW_SIZE + bbox.origin_y)
                    cv2.putText(self.last_frame, result_text, text_location, cv2.FONT_HERSHEY_PLAIN,
                                _FONT_SIZE, _TEXT_COLOR, _FONT_THICKNESS)
            else:
                    self.stopSign = False
            

        
    def getStopSign(self):
        print("stop Sign is Called : " , self.stopSign)
        return self.stopSign, self.ret, self.last_frame
    
    def terminate(self):
        print('terminating thread')
        self.running = False

if __name__ == '__main__':
    camera = cv2.VideoCapture(-1)
    camera.set(3, 320)
    camera.set(4, 240)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    objectDetectThread = JdObejctDetectThread(camera)
    
    while 1:
        isStop, isImg, stopImage = objectDetectThread.getStopSign()
        if isImg:
            cv2.imshow('object detection', stopImage)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            objectDetectThread.join()
            break
    camera.release()
    cv2.destroyAllWindows()
    
