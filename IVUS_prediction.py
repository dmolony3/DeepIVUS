from PyQt5.QtWidgets import QProgressDialog, QMessageBox 
from PyQt5.QtCore import Qt
import numpy as np
import os
import tensorflow as tf

IMG_MEAN = tf.constant([60.3486, 60.3486, 60.3486], dtype=tf.float32)
IMG_MEAN = tf.constant([60.3486], dtype=tf.float32)
num_classes = 4
num_phenotypes = 5
model_path = 'model/' # change this to relative filepath
#model_path =  '/home/microway/Documents/IVUS/model_2021'

try:
    model = tf.saved_model.load(model_path)
except:
    warning = ("Warning:  No saved weights have been found, segmentation will be unsuccessful, check that weights are saved in {}".format(os.path.join(os.getcwd(), 'model')))
    print(warning)
   
def cast_and_center(image):
    image = tf.cast(image, dtype=tf.float32)
    image = image - IMG_MEAN
    return image

def set_input_channels(images, channels=3):
    image_dim = images.get_shape()
    if len(image_dim) < 4:
        images = tf.expand_dims(images, axis=3)
    if image_dim[-1] != channels:
        images = tf.tile(images, [1, 1, 1, channels])
    return images
        
def predict(images):
    """Runs Convolutional Neural Network to predict image pixel class"""
    batch_size = 64
    dataset = tf.data.Dataset.from_tensor_slices((images))
    dataset = dataset.map(cast_and_center)
    dataset = dataset.batch(batch_size)
    num_batches = int(np.ceil(images.shape[0]/batch_size))
    
    """
    progress = QProgressDialog()
    progress.setWindowFlags(Qt.Dialog)
    progress.setModal(True)
    progress.setMinimum(0)  
    progress.setMaximum(num_batches - 1)
    progress.resize(500,100)
    progress.setValue(0)
    progress.setValue(1)
    progress.setValue(0) # trick to make progress bar appear
    progress.setWindowTitle("Segmenting images")
    progress.show()
    """
    pred = []
    pheno_pred_list = []
    for i, batch in enumerate(dataset):
        batch = set_input_channels(batch)
        logits = model(batch, training=False)
        logits = tf.image.resize(logits, (tf.shape(batch)[1], tf.shape(batch)[2]))
        pred.append(tf.argmax(logits, axis=-1, output_type=tf.dtypes.int32))
        print('Batch {} of {} completed'.format(i+1, num_batches))
        #progress.setValue(i)
        #if progress.wasCanceled():
        #    break

    #if progress.wasCanceled():
    #    return None

    #progress.close()
    pred = np.concatenate(pred)
    return pred

