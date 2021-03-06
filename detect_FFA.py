import argparse
from pathlib import Path
import os
import cv2
import torchvision
from PIL import Image
import numpy as np
from DMSHNet import DMSHN
from FFANet import FFA
from torch.utils.data import DataLoader
import torch
import torch.backends.cudnn as cudnn
from my_datasets import  LoadImages

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=str,
                    default='', help='source')
parser.add_argument('--task', type = str, default ='',
                    help='update all models')
opt = parser.parse_args()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
device_ids = [Id for Id in range(torch.cuda.device_count())]

FFA = FFA().to(device)
FFA = torch.nn.DataParallel(FFA, device_ids=device_ids)

def detect(opt , task ):

    source = opt.source
    dataset = LoadImages(source)

    if task == 'derain':
        FFA.load_state_dict(torch.load('FFA_derain.pth'  , map_location = 'cpu'))
    if task == 'denoisy':
        FFA.load_state_dict(torch.load('FFA_denoisy.pth', map_location = 'cpu'))
    if task == 'dehaze':
        FFA.load_state_dict(torch.load('FFA_dehaze.pth', map_location = 'cpu'))

    if task == 'enhencement':
        for path, img0, cap, mode in dataset:
          if mode == 'image':
             # clean = np.log10(img0) - np.log10(cv2.GaussianBlur(img0, (3, 3), 5))#retinex
             # clean = np.log10(img0)
             clean = 255.*((img0 + 1) / 255) ** 0.5 #gamma
             cv2.imwrite(f'runs/detect/clean.jpg', clean)
             return
          else:
              fps = cap.get(cv2.CAP_PROP_FPS)
              w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
              h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
              out = cv2.VideoWriter(f'runs/detect/clean.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps,
                                    (int(w / 2), int(h / 2)))

              while (cap.isOpened()):
                  ret_val, img = cap.read()
                  if ret_val:
                      img = 255. * ((img + 1) / 255) ** 0.5  # gamma
                      img = cv2.resize(img, (int(w / 2), int(h / 2)))
                      clean = np.ascontiguousarray(img).astype(np.uint8)
                      out.write(clean)
                  else:
                      break
              cap.release()
              out.release()
              return

    with torch.no_grad():
        FFA.eval()
        for path, img0, cap, mode in dataset:
           if mode == 'video':
                fps = cap.get(cv2.CAP_PROP_FPS)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                out = cv2.VideoWriter(f'runs/detect/clean.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps,
                                      (int(w / 2), int(h / 2)))
                while (cap.isOpened()):
                    ret_val, img = cap.read()
                    if ret_val :
                        img = cv2.resize(img, (int(w / 2), int(h / 2)))
                        img = img[:, :, ::-1].transpose(2, 0, 1)
                        img = np.ascontiguousarray(img)
                        img = torch.from_numpy(img).float()
                        img /= 255
                        img = img.to(device)
                        if img.ndimension() == 3:
                            img = img.unsqueeze(0)
                        clean, _ = FFA(img)

                        clean = torch.tensor(clean * 255 , dtype=torch.uint8)
                        clean = clean.cpu().numpy()
                        clean= clean.squeeze(0).transpose(1, 2, 0)
                        clean = clean[:, :, ::-1]
                        out.write(clean)
                    else:
                        break
                cap.release()
                out.release()
           else:
                for path, img0, cap, mode in dataset:
                    img0 = img0[:, :, ::-1].transpose(2, 0, 1)
                    img0 = np.ascontiguousarray(img0)
                    img0 = torch.from_numpy(img0).float() /255
                    img0 = img0.to(device)
                    if img0.ndimension() == 3:
                        img0 = img0.unsqueeze(0)
                    clean, _ = FFA(img0)
#                     torchvision.utils.save_image(clean, 'runs/detect/clean.jpg')
                    clean = clean.cpu().numpy()
                    clean = clean.squeeze(0).transpose(1, 2, 0)
                    clean = clean * 255
                    clean = clean[:, :, ::-1]
                    cv2.imwrite(f'runs/detect/clean.jpg', clean)


if __name__ == '__main__':
    detect(opt, opt.task)
