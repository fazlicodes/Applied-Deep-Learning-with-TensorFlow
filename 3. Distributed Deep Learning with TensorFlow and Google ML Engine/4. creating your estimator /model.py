import numpy as np
import tensorflow as tf
from tensorflow import feature_column
from tensorflow.python.lib.io import file_io
tf.logging.set_verbosity(tf.logging.INFO)
from pprint import pprint 
from tensorflow.python import debug as tf_debug
hook = tf_debug.TensorBoardDebugHook("PA-M-CRAMSEY:8889")



# DESCRIBE DATASET
# define columns and field defaults
COLUMNS        = ["Lat", "Long", "Altitude","Date_",
                  "Time_", "dt_", "y"]
FIELD_DEFAULTS = [[0.], [0.], [0.], ['na'],
                  ['na'], ['na'], ['na']]
feature_names = COLUMNS[:-1]

# FEATURE COLUMNS
## represent feature columns
# dense feature_columns
lat      = tf.feature_column.numeric_column("Lat")
lng      = tf.feature_column.numeric_column("Long")
altitude = tf.feature_column.numeric_column("Altitude")

# sparse feature_columns
date_ = tf.feature_column.categorical_column_with_hash_bucket('Date_', 100)
time_ = tf.feature_column.categorical_column_with_hash_bucket('Time_', 100)
dt_ = tf.feature_column.categorical_column_with_hash_bucket('dt_', 100)

lat_long_buckets = list(np.linspace(-180.0, 180.0, num=30))

lat_buck  = tf.feature_column.bucketized_column(
    source_column = lat,
    boundaries = lat_long_buckets )

lng_buck = tf.feature_column.bucketized_column(
    source_column = lng,
    boundaries = lat_long_buckets)

real_feature_columns  = [lat, lng, altitude]
sparse_feature_columns  =  [date_, time_, dt_, lat_buck, lng_buck ]
all_feature_columns = real_feature_columns + sparse_feature_columns

# define input pipeline
def my_input_fn(file_paths, perform_shuffle=True,  batch_size=32):
    def decode_csv(line):
        parsed_line = tf.decode_csv(line, FIELD_DEFAULTS)
        label = tf.convert_to_tensor(parsed_line[-1:])
        del parsed_line[-1]  # Delete last element
        features = parsed_line  # Everything (but last element) are the features
        d = dict(zip(feature_names, features)), label
        return d

    dataset = (tf.data.TextLineDataset(file_paths)  # Read text file
                    .skip(1)
                    .map(decode_csv))  # Transform each elem by decode_csv
    if perform_shuffle:
        dataset = dataset.shuffle(256)
    dataset = dataset.batch(batch_size)
    
    iterator = dataset.make_one_shot_iterator()
    batch_features, batch_labels = iterator.get_next()
    return batch_features, batch_labels

# define all class labels
class_labels = ['bike', 'bus', 'car', 
                'driving meet conjestion', 
                'plane', 'subway', 'taxi', 
                'train', 'walk']
                     
def train_eval(traindir, evaldir, batchsize, epochs, outputdir, **kwargs):
    # define classifier config
    classifier_config=tf.estimator.RunConfig(save_checkpoints_steps=100)
    
    # define classifier
    classifier = tf.estimator.DNNLinearCombinedClassifier(
        linear_feature_columns=all_feature_columns,
        dnn_feature_columns=real_feature_columns,
        dnn_hidden_units = [90,40,12],
        n_classes=len(class_labels),
        label_vocabulary=class_labels,
        dnn_dropout=.2,
        model_dir=outputdir,
        config=classifier_config
    )

    # load training and eval files    
    traindata =   [file for file in file_io.get_matching_files(
        traindir + '/trajectories.csv*')]
    evaldata =    [file for file in file_io.get_matching_files(
        evaldir + '/trajectories.csv*')]

    # define training and eval params
    train_input = lambda: my_input_fn(
            traindata,
            batch_size=batchsize,
            perform_shuffle=True
        )

    eval_input = lambda: my_input_fn(
        evaldata,
        batch_size=99999999,
        perform_shuffle=False
    )

    # define training, eval spec for train and evaluate including
    train_spec = tf.estimator.TrainSpec(train_input, 
                                        max_steps=10000,
                                        hooks = [hook]
                                        )
    eval_spec = tf.estimator.EvalSpec(eval_input,
                                    name='trajectory-eval'
                                    )                                  
    # run training and evaluation
    tf.estimator.train_and_evaluate(
        classifier, train_spec, eval_spec)


train_eval(traindir='../data/train', 
    evaldir='../data/test', batchsize=10, epochs=2, outputdir='outputdir')