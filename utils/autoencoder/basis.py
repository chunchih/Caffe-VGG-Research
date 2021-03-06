import sys
caffe_root = '../../../../'  # this file is expected to be in {caffe_root}/examples
ml_root = '../../'
sys.path.append(caffe_root + 'python')
import caffe # If you get "No module named _caffe", either you have not built pycaffe or you have the wrong path.
from caffe import layers as L, params as P # Shortcuts to define the net prototxt.

sys.path.append(ml_root + "pycaffe/layers") # the datalayers we will use are in this directory.
sys.path.append(ml_root + "pycaffe") # the tools file is in this folder

# helper function for common structures
def conv(bottom, k_w, k_h, nout, stride=1, pad=0, group=1, no_back=False):
	if no_back is False:
		conv = L.Convolution(bottom, kernel_w=k_w, kernel_h=k_h, stride=stride, num_output=nout, pad=pad, group=group, weight_filler=dict(type='gaussian',std=0.01), bias_filler=dict(type='constant', value=0))
	else:
		conv = L.Convolution(bottom, kernel_w=k_w, kernel_h=k_h, stride=stride, num_output=nout, pad=pad, group=group, weight_filler=dict(type='gaussian',std=0.01), bias_filler=dict(type='constant', value=0),param=[dict(lr_mult=0, decay_mult=0),dict(lr_mult=0, decay_mult=1)])
    
	return conv

def conv_relu(bottom, k_w, k_h, nout, stride=1, pad=0, group=1, no_back=False):
	conv_out = conv(bottom, k_w, k_h, nout, stride, pad, group, no_back)
	return conv_out, L.ReLU(conv_out, in_place=True)


# yet another helper function
def max_pool(bottom, ks, stride=1):
	return L.Pooling(bottom, pool=P.Pooling.MAX, kernel_size=ks, stride=stride)

