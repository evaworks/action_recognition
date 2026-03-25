"""动作识别主入口"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pose_camera import create_pose_camera


def main():
    parser = argparse.ArgumentParser(description='基于YOLOv11-Pose的动作识别系统')
    parser.add_argument('--model', type=str, default='models/yolo11s-pose.pt',
                       help='YOLO模型路径，默认为yolo11s-pose.pt')
    parser.add_argument('--config', type=str, default=None,
                       help='配置文件目录，默认为config目录')
    parser.add_argument('--camera', type=int, default=0,
                       help='摄像头索引，默认为0')
    parser.add_argument('--debug', action='store_true',
                       help='显示调试信息')
    parser.add_argument('--hidden', action='store_true',
                       help='隐藏窗口后台运行')
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    if args.config is None:
        args.config = os.path.join(project_root, 'config')
    
    if not os.path.exists(args.model):
        print(f"警告: 模型文件 {args.model} 不存在，将自动下载...")
    
    print("="*50)
    print("  基于YOLOv11-Pose的动作识别系统")
    print("="*50)
    print(f"模型: {args.model}")
    print(f"配置目录: {args.config}")
    print(f"摄像头: {args.camera}")
    print("="*50)

    pose_camera = create_pose_camera(
        model_path=args.model,
        config_dir=args.config
    )
    
    try:
        pose_camera.run(camera_index=args.camera, debug=args.debug, hidden=args.hidden)
    except KeyboardInterrupt:
        print("\n\n用户中断程序")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pose_camera.release()


if __name__ == '__main__':
    main()
