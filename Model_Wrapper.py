# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 18:14:28 2020

@author: junaid

"""

from tensorflow.keras.layers import Conv3D,ConvLSTM2D,Conv3DTranspose, Input
from tensorflow.keras.models import Model
from tensorflow.compat.v1.keras.backend import set_session
import tensorflow as tf
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import cv2
import sys
#from tensorflow.keras.models import load_model

def BuildModel(input_shape=(227,227,10,1)):
    '''
    Architenture of the model is built here, Convolutional layers, LSTM 
    layers and all.

    Parameters
    ----------
    input_shape : tuple, optional
      Dimensions of the input that will be feed to the model. The default is (227,227,10,1).

    Raises
    ------
    ValueError
      Input shape must have 4 values height, width, frames-per-input and channels.

    Returns
    -------
    model : 
      Complete architecture of the model.

    '''
    if len(input_shape) != 4 or type(input_shape) != tuple:
        raise ValueError('Invalid value given to the argument `input_shape`, it must be a `tuple` containing 4 values in this manner: (height, width, frames_per_input, channels)')
    input = Input(shape=input_shape)
    #Spatial Encoder
    spatial_enc = Conv3D(filters=128, kernel_size=(11,11,1), strides=(4,4,1), padding='valid', activation='tanh')(input)
    spatial_enc = Conv3D(filters=64, kernel_size=(5,5,1), strides=(2,2,1), padding='valid', activation='tanh')(spatial_enc)

    #Temporal Encoder
    temporal_enc = ConvLSTM2D(filters=64,kernel_size=(3,3),strides=1,padding='same',dropout=0.4,recurrent_dropout=0.3,return_sequences=True)(spatial_enc)
    temporal_enc = ConvLSTM2D(filters=32,kernel_size=(3,3),strides=1,padding='same',dropout=0.3,return_sequences=True)(temporal_enc)

    #Temporal Decoder
    temporal_dec = ConvLSTM2D(filters=64,kernel_size=(3,3),strides=1,return_sequences=True, padding='same',dropout=0.5)(temporal_enc)

    #Spatial Decoder
    spatial_dec = Conv3DTranspose(filters=128,kernel_size=(5,5,1),strides=(2,2,1),padding='valid',activation='tanh')(temporal_dec)
    spatial_dec = Conv3DTranspose(filters=1,kernel_size=(11,11,1),strides=(4,4,1),padding='valid',activation='tanh')(spatial_dec)

    #Compiling Model
    model = Model(inputs=input, outputs=spatial_dec)
    model.summary()
    model.compile(optimizer='adam',loss='mean_squared_error',metrics=['accuracy'])
    return model

def TF_GPUsetup():
    '''
    A function to setup the GPU.

    Returns
    -------
    None.
    '''
    print('\nTensorflow GPU installed: '+str(tf.test.is_built_with_cuda()))
    print('Is Tensorflow using GPU: '+str(tf.test.is_gpu_available()))
    config = tf.compat.v1.ConfigProto()
    config.gpu_options.allow_growth = True  # dynamically grow the memory used on the GPU
    config.log_device_placement = True  # to log device placement (on which device the operation ran)
    sess = tf.compat.v1.Session(config=config)
    set_session(sess)
    sess.as_default()

def PrepareData(X_train, re_shape=(-1,227,227,10)):
    '''
    It prepares the training data, so that it could be 
    feed to the model for training.

    Parameters
    ----------
    X_train : 
      The training data from the numpy array stored in PreProcessing_V5 file.
    re_shape : tuple, optional
      Tuple to reshape the training data which will be feed to the model 
      for training. The default is (-1,227,227,10).

    Returns
    -------
    X_train :
      Training Data inaccordance to the requirments of the model.

    '''
    frames = X_train.shape[2]
    #Need to make number of frames divisible by 10
    frames -= frames%10
    
    X_train=X_train[:,:,:frames]
    X_train=X_train.reshape(re_shape)
    X_train=np.expand_dims(X_train,axis=4)
    return X_train
    

def GetTrainData(name, re_shape=(-1,227,227,10)):
    '''
    An other mini function that calls PrepareData to prepare the data
    for begin training.

    Parameters
    ----------
    name : string
      Name to the numpy array from where it will prepare the data.
    re_shape : tuple, optional
      Tuple to reshape the training data. The default is (-1,227,227,10).

    Raises
    ------
    TypeError
      Name to the numpy array file should be valid from where it will read the dataset and
      prepare into batches inaccorance to the needs of model.
      
    Returns
    -------
    Returns a prepared training data ready for training.

    '''
    if type(name)!=str:
        raise TypeError('Provide a valid name of `string` datatype, to the `.npy` file.')
    if '.npy' not in name:
        name += '.npy'
    X_train = np.load(name)
    return PrepareData(X_train, re_shape)

def OverlayText2Img(img, text, fill = False):
    '''
    This function takes the image/frame that has been from 
    prediction process and overlays the Text on that frame
    to tag if its normal frame or anomalous.

    Parameters
    ----------
    img : 
      One by one frame.
    text : 
      The text that will be overlayed onto the frame.

    Returns
    -------
    im_pros : 
      A tagged frame showing its type (Normal/Anomalous).

    '''
    # Convert to PIL Image
    cv2_im_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(cv2_im_rgb)
    draw = ImageDraw.Draw(pil_im)
    
    # Choose a font
    font = ImageFont.truetype("arial.ttf", 40)
    
    # Draw the text
    if fill == True:
      draw.text((1, 5), text, font=font, fill = 'red')
      draw.rectangle([(0,0),(357,50)], outline = 'red')
    
    else:
      draw.text((0,0), text, font = font, fill = 'green')
      draw.rectangle([(0,0),(130,50)], outline = 'green')
    # Save the image
    im_pros = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return im_pros

def ShowVideo(cap, v_frame, text, fill = False):
    """
    This function is used to show the video in real time,
    and also show the prediction from the model overit.
    Parameters
    ----------
    cap :
        Object to the cv2.VideoCapture() class.
    v_frame :
        Video frame that will be sent to 'OverlayText2Img'.
    text : 
        Text that will be overlayed onto the frame.
    Returns
    -------
    None.
    """
    if fill == True:
      v_frame = OverlayText2Img(v_frame, text, fill = True)
    else:
      v_frame = OverlayText2Img(v_frame, text)
    #cv2.namedWindow('image', cv2.WINDOW_NORMAL)
    cv2.imshow('Real Time Anomaly Detection',v_frame)
    # Press Q on keyboard to  exit
    if cv2.waitKey(25) & 0xFF == ord('q'):
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        raise KeyboardInterrupt('Real Time Anomoly Detection Stopped due to Keyboard Interrupt!') 
            
def PrintInline(string):
    '''
    A function to print the information on one single line, as
    in for loop it may print information on each new line, so to avoid 
    that this function is used.

    Parameters
    ----------
    string : 
      Information to be displayed.

    Returns
    -------
    None.
    
    '''
    sys.stdout.write('\r'+string)
    sys.stdout.flush() 

def ImgProcess(frame, shape=(227,227)):
    '''
    A mini function for the processing of the images for testing the model.

    Parameters
    ----------
    frame : 
      Input frame.
    shape : tuple, optional
      Tuple for resizing the image/frame. The default is (227,227).
      
    Returns
    -------
    gray :
      Returns processed gray scale frame/image.

    '''
    frame=cv2.resize(frame,shape)
    rgb_weights = [0.2989, 0.5870, 0.1140]
    gray = np.dot(frame, rgb_weights)
    gray=(gray-gray.mean())/gray.std()
    gray=np.clip(gray,0,1)
    return gray

def Img_LstArr(img_lst, re_shape=(227, 227, 10)):
    '''
    This function is used to convert the Image lists 
    back to array, so that it could be displayed.

    Parameters
    ----------
    img_lst : list
      The image list that needs to be converted back to array.
    re_shape : tuple, optional
      A tuple to resize the array. The default is (227, 227, 10).

    Returns
    -------
    img_arr : 
      Returns array of the images that are converted from lists.

    '''
    img_arr=np.array(img_lst)
    img_arr.resize(re_shape)
    img_arr=np.expand_dims(img_arr,axis=0)
    img_arr=np.expand_dims(img_arr,axis=4)
    return img_arr

def MSE(x1,x2):
    """
    Compute Euclidean Distance Loss between input frame and the reconstructed frame and then
    compute the Mean Squared Error
    Parameters
    ----------
    x1 : 
        Input frame.
    x2 : 
        Rrconstructed frame.
    Returns
    -------
    mean_dist : 
        Calculated mean squared error.
    """
    diff=x1-x2
    a,b,c,d,e=diff.shape
    n_samples=a*b*c*d*e
    sq_diff=diff**2
    Sum=sq_diff.sum()
    dist=np.sqrt(Sum)
    mean_dist=dist/n_samples
    
    return mean_dist

def ListCopy(lst):
    '''
    Def:
      As we have lists with in lists (For dataset paths), so this function
      just get the main data and creates a new list that only have the complete 
      path to the data from the datasets.

    '''  
    new_lst = []
    for item_lst in lst:
        for item in item_lst:
            #ten_lst = []
            new_lst.append(item)        
    return new_lst