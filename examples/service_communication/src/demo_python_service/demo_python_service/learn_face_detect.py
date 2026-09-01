import face_recognition
import cv2
from ament_index_python.packages import get_package_share_directory #获取功能包share目录绝对路径
import os

def main():
    # 获取图片绝对路径 /home/numblime/chapt4/chapt4_ws/install/demo_python_service/share/demo_python_service/resource/default.jpg
    default_image_path = os.path.join(get_package_share_directory('demo_python_service'), 
                                      'resource', 'default.jpg')
    print(f"图片绝对路径: {default_image_path}")
    # 使用cv2读取图片
    image = cv2.imread(default_image_path)
    # 使用face_recognition库进行人脸检测
    face_locations = face_recognition.face_locations(image,
                            number_of_times_to_upsample=1, model="hog")
    # 绘制人脸检测结果
    for (top, right, bottom, left) in face_locations:
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 4)
    # 显示检测结果
    cv2.imshow("Detected Faces", image)
    cv2.waitKey(0)    