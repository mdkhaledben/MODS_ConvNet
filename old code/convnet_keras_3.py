"""
Created on Tue Jul 19 10:18:36 2016

@author: SLG
"""

import keras
from keras.models import Sequential
from keras.preprocessing.image import ImageDataGenerator
from keras.layers.core import Dense, Dropout, Activation, Flatten
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.optimizers import SGD
import cPickle
import math
import numpy as np
from keras.regularizers import l1l2
from keras.layers.normalization import BatchNormalization
from keras.callbacks import EarlyStopping
#from scipy.stats import ttest_ind

class LossHistory(keras.callbacks.Callback):
    def on_train_begin(self, logs={}):
        self.losses = []

    def on_batch_end(self, batch, logs={}):
        self.losses.append(logs.get('loss'))
        

def get_data(n_dataset):    
    f = file('MODS_dataset_cv_{0}.pkl'.format(n_dataset),'rb')
    data = cPickle.load(f)
    f.close()
    training_data = data[0]
    validation_data = data[1]
    t_data = training_data[0]
    t_label = training_data[1]
    v_data = validation_data[0]
    v_label = validation_data[1]
    
    t_data = np.array(t_data)
    t_label = np.array(t_label)
    v_data = np.array(v_data)
    v_label = np.array(v_label)
    t_data = t_data.reshape(t_data.shape[0], 1, 256, 192)
    v_data = v_data.reshape(v_data.shape[0], 1, 256, 192)
    
    #less precision means less memory needed: 64 -> 32 (half the memory used)
    t_data = t_data.astype('float32')
    v_data = v_data.astype('float32')
    
    return t_data, t_label, v_data, v_label

def network(regl1, regl2, weight_init, dropout, optimize):   
    
    #create network architecture
    model = Sequential()
    
    model.add(Convolution2D(16, 7, 7,input_shape=(1, 256, 192),W_regularizer=l1l2(l1=regl1, l2=regl2),init=weight_init))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(dropout))
    
    model.add(Convolution2D(32, 6, 6, W_regularizer=l1l2(l1=regl1, l2=regl2),init=weight_init))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))  
    model.add(Dropout(dropout))
    
    model.add(Convolution2D(64, 3, 3, W_regularizer=l1l2(l1=regl1, l2=regl2),init=weight_init))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))  
    model.add(Dropout(dropout))
    
    model.add(Convolution2D(64, 2, 2, W_regularizer=l1l2(l1=regl1, l2=regl2),init=weight_init))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))  
    model.add(Dropout(dropout))
    
    model.add(Flatten())
    model.add(Dense(50,W_regularizer=l1l2(l1=regl1, l2=regl2),init=weight_init))
    #model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    
    model.add(Dense(output_dim=1))
    model.add(Activation('sigmoid'))    

    model.compile(optimizer=optimize, loss='binary_crossentropy', metrics=['accuracy'])
    
    return model

def cv_calc(regl1, regl2, weight_init, dropout, optimize, bsize, n_dataset):
    
    #conditions for training, where early stopping stops the network training if validation accuracy does not increase
    early_stopping = EarlyStopping(monitor='val_loss', patience=6)
    history = LossHistory()
    
    #creates a dictionary of parameters and their values
    dict_param = {'Regularization L1': regl1, 'Regularization L2': regl2, 'Weight initialization': weight_init, 
                  'Dropout': dropout, 'Optimizer': str(optimize), 'Mini batch size': bsize}
                  
    #creates a list of metrics according to dataset
    param_metrics = []
                  
    #for each dataset, loads the model, the data, and calculates metrics

    X_train, Y_train, X_val, Y_val = get_data(n_dataset)
    print 'training on dataset ' + str(n_dataset)
    model = network(regl1, regl2, weight_init, dropout, optimize)
    
    train_datagen = ImageDataGenerator(
            rotation_range=45,
            horizontal_flip=True,
            vertical_flip=True)
            #width_shift_range=0.5, 
            #height_shift_range=0.5)

    train_datagen.fit(X_train)
    
    train_generator = train_datagen.flow(
                X=X_train, 
                y=Y_train, 
                batch_size=bsize, 
                shuffle=True)
                #save_to_dir='/home/musk/MODS_data')
    
    model.fit_generator(train_generator, samples_per_epoch=len(X_train), nb_epoch=30, callbacks = [early_stopping, history]) 

    #model.fit_generator(train_datagen.flow(X_train, Y_train, batch_size=bsize),
    #            samples_per_epoch=len(X_train), nb_epoch=3, callbacks = [early_stopping, history]) 
                
    
    prediction = model.predict(X_val,batch_size=Y_val.shape[0])

    prediction[prediction > 0.5] = 1.0
    prediction[prediction <= 0.5] = 0.0
    
    F1 = 0.0
    mcc = 0.0
    
    TP = 0
    for i in xrange(len(Y_val)):
        if Y_val[i] == 1.0 and prediction[i] == 1.0:
			TP+=1.0
    
    TN = 0
    for i in xrange(len(Y_val)):
        if Y_val[i]  == 0.0 and prediction[i] == 0.0:
            TN+= 1.0
     
    FP = 0
    for i in xrange(len(Y_val)):
        if Y_val[i] < prediction[i]:
            FP+= 1.0

    FN = 0
    for i in xrange(len(Y_val)):
        if Y_val[i] > prediction[i]:
            FN+= 1.0
    
    print (TP, TN, FP, FN)
    
    sensitivity = TP/(TP + FN)
    specificity = TN/(TN + FP)
    
    print (sensitivity, specificity)
    
    print('Test Sensitivity Score: {0:.2%}'.format(sensitivity))
    print('Test Specificity Score: {0:.2%}'.format(specificity))
    
    try:
        PPV = TP / (TP + FP)
        NPV = TN / (TN + FN)
        F1 = 2.0 * (PPV * sensitivity)/(PPV + sensitivity)
        mcc = (TP*TN - FP*FN)/(math.sqrt((TP + FP)*(TP + FN)*(TN + FP)*(TN + FN)))
        print('Test F1 Score: {0:.2}'.format(F1))
    
    
    except ZeroDivisionError:
        print('Divide by Zero')
        F1 = None
        mcc = None
        PPV = None
        NPV = None
        
    
    param_metrics.append([sensitivity, specificity, F1, PPV, NPV, mcc])
    score = model.evaluate(X_val, Y_val, verbose=0)
    print('Test loss:', score[0])
    print('Test accuracy:', score[1])
    
    param_metrics = np.array(param_metrics)
    stat = [dict_param, param_metrics]
    
    return stat, model, history, potato

#Hyperparameters for tuning
weight_init = ['he_normal','glorot_normal']
regl1 = [1.0, 0.1, 0.01, 0.001, 0.0]
regl2 = [1.0, 0.1, 0.01, 0.001, 0.0]
dropout = [0.0, 0.25, 0.5, 0.7]
bsize = [32] #[32, 70, 100, 150]
learning_rate = [0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3]
optimizer = ['sgd', 'adadelta']

n_dataset = 5

for i in weight_init:
    for j in regl1:
        for k in regl2:
            for l in dropout:
                for m in bsize:
                    for n in optimizer:
                        if n =='sgd':
                            for o in learning_rate:
                                sgd = SGD(lr=o, decay=1e-6, momentum=0.9, nesterov=True)
                                for potato in xrange(n_dataset):
                                    stat, model, history, dataset = cv_calc(regl1 = j, regl2 = k , weight_init = i, dropout = l, optimize = sgd, bsize = m, n_dataset = potato)
                                    
                                    '''save model in HDF5 file - it will contain architecture of the model, weights, 
                                    training configuration, and state of the optimizer
                                    -> I actually can't get this to work ATM,
                                    so I'll stick to saving model and weights separately'''
                                    #save model
                                    #name = 'MODS_keras_model_{0}_{1}_{2}_{3}_{4}_{5}_{6}.h5'.format(n_dataset, j, k, i, l, sgd, m)
                                    #model.save(name)
                                    #del model
                                    json_string = model.to_json()
                                    name = 'MODS_keras_model_{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}.json'.format(dataset, j, k, i, l, 'sgd', m, o)
                                    open(name, 'w').write(json_string)
                                    print 'model saved'
                                    
                                    
                                    #Save weights
                                    name = 'MODS_keras_weights_{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}.h5'.format(dataset, j, k, i, l, 'sgd', m, o)
                                    model.save_weights(name, overwrite=True)
                                    print('weights saved')
                                    
                                    #save loss
                                    f = open('MODS_keras_loss_{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}.pkl'.format(dataset, j, k, i, l, 'sgd', m, o),'wb')
                                    cPickle.dump(history.losses,f,protocol=cPickle.HIGHEST_PROTOCOL)
                                    f.close()
                                    print('loss saved')
                                    
                                    #save metrics 
                                    name = 'MODS_keras_metrics_{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}.txt'.format(dataset, j, k, i, l, 'sgd', m, o)
                                    h = open(name, 'w')
                                    param = str(stat[0])
                                    metrics = str(stat[1])
                                    h.write(param)
                                    h.write(metrics)
                                    h.close()


                                    print('metrics saved')
                                    
                                    
                                    model.reset_states()
                        else:
                            for potato in xrange(n_dataset):
                                stat, model, history, dataset = cv_calc(regl1 = j, regl2 = k , weight_init = i, dropout = l, optimize = 'adadelta', bsize = m, n_dataset = potato)                            
                                
                                #save model
                                #name = 'MODS_keras_model_{0}_{1}_{2}_{3}_{4}_{5}_{6}.h5'.format(n_dataset, j, k, i, l, 'adadelta', m)
                                #model.save(name)
                                #del model
                                json_string = model.to_json()
                                name = 'MODS_keras_model_{0}_{1}_{2}_{3}_{4}_{5}_{6}.json'.format(dataset, j, k, i, l, 'adadelta', m)
                                open(name, 'w').write(json_string)
                                print 'model saved'
                                
                                #Save weights
                                name = 'MODS_keras_weights_{0}_{1}_{2}_{3}_{4}_{5}_{6}.h5'.format(dataset, j, k ,  i, l,'adadelta',m)
                                model.save_weights(name,overwrite=True)
                                print('weights saved')
                                
                                #save loss
                                f = open('MODS_keras_loss_{0}_{1}_{2}_{3}_{4}_{5}_{6}.pkl'.format(dataset, j, k ,  i, l,'adadelta', m),'wb')
                                cPickle.dump(history.losses,f,protocol=cPickle.HIGHEST_PROTOCOL)
                                f.close()
                                print('loss saved')
    
                                #save metrics
                                name = 'MODS_keras_metrics_{0}_{1}_{2}_{3}_{4}_{5}_{6}.txt'.format(dataset, j, k ,  i, l,'adadelta', m)
                                h = open(name, 'w')
                                param = str(stat[0])
                                metrics = str(stat[1])
                                h.write(param)
                                h.write(metrics)
                                h.close()
                                print('metrics saved')
    
                                model.reset_states()

print 'finished hyperparameter search!'



 
'''
##To compare models and return the best 5, according to sensitivity
def compare_data(best_models,stat,model):
    sens = stat[1][0,:]
    for m in xrange(len(best_models)):
        sens_best = best_models[m][1]
        None, p_value = ttest_ind(sens,sens_best)
        if p_value < 0.05:
            best_models[m] = [stat[0],sens,model]
            break
    return best_models
best_models = []


	#l = h5py.File("loss_history_{0}.hdf5".format(number_db), "w")
	#dset = f.create_dataset("loss_history_{0}".format(number_db), (100,), dtype='i')

NB: 	#A way to open a model with weights in the same arquitecture
json_string = model.to_json()
open('my_model_architecture.json', 'w').write(json_string)
model.save_weights('my_model_weights.h5')  

'''

