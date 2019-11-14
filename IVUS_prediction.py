import tensorflow as tf
import numpy as np

IMG_MEAN = tf.constant([60.3486, 60.3486, 60.3486], dtype=tf.float32)
IMG_MEAN = tf.constant([60.3486], dtype=tf.float32)
num_classes = 4
num_phenotypes = 5
model_path = '/home/microway/Documents/IVUS/Segmentation2.0/deepIVUS_blurpool_48_serialized/' # change this to relative filepath


def cast_and_center(image):
    image = tf.cast(image, dtype=tf.float32)
    image = image - IMG_MEAN
    return image

def set_input_channels(images, channels=3):
    image_dim = images.get_shape()
    if len(image_dim) < 4:
        images = tf.expand_dims(image, axis=3)
    if image_dim[-1] != channels:
        images = tf.tile(images, [1, 1, 1, channels])
    return images
        
def predict(images):
    batch_size = 16
    model = tf.saved_model.load(model_path)

    dataset = tf.data.Dataset.from_tensor_slices((images))
    dataset = dataset.map(cast_and_center)
    dataset = dataset.batch(batch_size)
    
    pred = []
    pheno_pred_list = []
    for i, batch in enumerate(dataset):
        batch = set_input_channels(batch)
        logits = model(batch, training=False)
        logits = tf.image.resize(logits, (tf.shape(batch)[1], tf.shape(batch)[2]))
        pred.append(tf.argmax(logits, axis=-1, output_type=tf.dtypes.int32))
    pred = np.concatenate(pred)
    return pred
