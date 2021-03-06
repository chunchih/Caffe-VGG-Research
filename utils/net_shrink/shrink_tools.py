import sys
caffe_root = '../../../../'  # this file is expected to be in {caffe_root}/examples
ml_root = '../../'
import os
import os.path as osp
import numpy as np
sys.path.append(caffe_root + 'python')
import caffe # If you get "No module named _caffe", either you have not built pycaffe or you have the wrong path.
from caffe import layers as L, params as P # Shortcuts to define the net prototxt.

sys.path.append(ml_root + "pycaffe/layers") # the datalayers we will use are in this directory.
sys.path.append(ml_root + "pycaffe") # the tools file is in this folder
sys.path.append(ml_root + "pycaffe/net_shrink")
from nets import *
import heapq
import tools_gray as tools#this contains some tools that we need


from basis import *

class Create_prototxt:
	def __init__(self, working_folder,policy, batch_sz, data_list, stepsize, train_file, val_file):

	    self.working_folder = working_folder 
	    self.batch_sz = batch_sz
	    self.data_list = data_list
	    self.train_file = train_file
	    self.val_file = val_file
	    self.policy = policy
	    self.stepsize = stepsize

	    if os.path.isdir(osp.join(working_folder, "prototxt")) is False:
	        os.makedirs(osp.join(working_folder, "prototxt"))

	def make_prototxt(self, name, fc_num, folder):	    

	    t_prototxt = "trainnet" + name
	    s_prototxt = "solver" + name
	    v_prototxt = "valnet" + name
	    d_prototxt = "deploynet" + name
	    prototxt_folder = osp.join(self.working_folder, "prototxt", folder)

	    solverprototxt = tools.CaffeSolver(trainnet_prototxt_path = osp.join(prototxt_folder, t_prototxt), testnet_prototxt_path = osp.join(prototxt_folder, d_prototxt))

	    solverprototxt.sp['base_lr'] = "0.001"
	    solverprototxt.sp['gamma'] = "0.1"
	    solverprototxt.sp['display'] = "50"
	    solverprototxt.sp['snapshot'] = "5000"
	    solverprototxt.sp['test_interval'] = "200000"#str(self.stepsize*50)
	    

	    if self.policy == "step":
		solverprototxt.sp['lr_policy'] = "\"step\""
		solverprototxt.sp['stepsize'] = str(self.stepsize)
	    
	    if os.path.isdir(prototxt_folder) is False:
		os.makedirs(prototxt_folder)
		
	    solverprototxt.write(osp.join(prototxt_folder, s_prototxt))    
	    print osp.join(prototxt_folder, s_prototxt)
	    


	    with open(osp.join(prototxt_folder, t_prototxt), 'w') as f:
		f.write(caffenet_multilabel_vgg(self.train_file, self.batch_sz, [4,13], fc_num))    
	    print osp.join(prototxt_folder, t_prototxt)
	    
	    # write validation net.
	    with open(osp.join(prototxt_folder, v_prototxt), 'w') as f:
		f.write(caffenet_multilabel_vgg(self.val_file, self.batch_sz, [4,13], fc_num))    
	    print osp.join(prototxt_folder, v_prototxt)
	    
	    with open(osp.join(prototxt_folder, d_prototxt), 'w') as f:
		f.write(caffenet_vgg_input(128, [4,13], fc_num, False)) 
	    print osp.join(prototxt_folder, d_prototxt)


def compute_rmse(img1, img2):
    return np.sqrt(((img1 - img2) ** 2).mean())

def compute_weight_rmse(f_map, shape, bound):
    if bound == 0:
        return []

    remove_idx = []
    size = f_map.shape[0]
    rmse = [compute_rmse(r,np.zeros((shape[1],shape[2],shape[3]))) for r in f_map]
    rmse_back = []
    rmse_max = np.max(rmse)
    while(len(remove_idx) < shape[0]):
        rmse_min = np.argmin(rmse)
	rmse_back.append(rmse[rmse_min])
        remove_idx.append(rmse_min)
        rmse[rmse_min] = rmse_max+1
    idx = [r for e, r in enumerate(remove_idx) if r not in remove_idx[:e]]
    return idx[:bound]

def count_parameter_by_fc(fc1, fc2, output_class):

	fc1 = 4096-int(fc1)
	fc2 = 4096-int(fc2)
	origin = 4041728 + 4096*(512*4*13+1)+4096*(4096+1)+output_class*(4096+1)
	total = 4041728 + fc1*(512*4*13+1)+fc2*(fc1+1)+output_class*(fc2+1)

	return total, float(origin)/total

def shrink_fc(pro, working_folder, fc_num_o, fc_num_n, hide_num):
	
	postfix_o = "_fc1_%d_fc2_%d.prototxt" % (4096-fc_num_o[0], 4096-fc_num_o[1])
	pro.make_prototxt(postfix_o, fc_num_o, str(4096-fc_num_o[0]))
	solver_t = caffe.SGDSolver(osp.join(working_folder, "prototxt", str(4096-fc_num_o[0]), "solver"+postfix_o))	
	solver_t.net.copy_from(osp.join(working_folder,"models",str(4096-fc_num_o[0]),"snap_fc1_%d_fc2_%d.caffemodel"%(4096-fc_num_o[0], 4096-fc_num_o[1])))
	if fc_num_o[0] == fc_num_n[0] and fc_num_o[1] == fc_num_n[1]:
		return solver_t
	
	hide_idx_1 = compute_weight_rmse(solver_t.net.params['fc1'][0].data, solver_t.net.params['fc1'][0].data.shape, fc_num_o[0]-fc_num_n[0])
	hide_idx_2 = compute_weight_rmse(solver_t.net.params['fc2'][0].data, solver_t.net.params['fc2'][0].data.shape, fc_num_o[1]-fc_num_n[1])

	postfix_n = "_fc1_%d_fc2_%d.prototxt" % (4096-fc_num_n[0], 4096-fc_num_n[1])
	pro.make_prototxt(postfix_n, fc_num_n, str(4096-fc_num_n[0]))
	solver_d = caffe.SGDSolver(osp.join(working_folder, "prototxt", str(4096-fc_num_n[0]), "solver"+postfix_n))
	
	params_d = solver_d.net.params.keys()
    	
	# Hide the hiden idx in Origin Model to New Model
	for p in params_d:
		print p
		if p == 'fc_class':
			fg = 0	
			for e in range(solver_t.net.params['fc_class'][0].data.shape[1]):
				if e in hide_idx_2:
					fg += 1
					continue

				solver_d.net.params['fc_class'][0].data[:,e-fg,:,:] = solver_t.net.params['fc1'][0].data[:,e,:,:]

		elif p == 'fc2':
			fg1 = 0				
			for e1 in range(solver_t.net.params['fc2'][0].data.shape[0]):
				fg2 = 0
				for e2 in range(solver_t.net.params['fc2'][0].data.shape[1]):
					if e1 in hide_idx_2:
						fg1 += 1
						break

					if e2 in hide_idx_1:
						fg2 += 1
						continue

					solver_d.net.params['fc2'][0].data[e1-fg1,e2-fg2,:,:] = solver_t.net.params['fc2'][0].data[e1,e2,:,:]
					solver_d.net.params['fc2'][1].data[e1-fg1] = solver_t.net.params['fc2'][0].data[e1]


		elif p == 'fc1':
			fg = 0	
			for e in range(solver_t.net.params['fc1'][0].data.shape[0]):
				if e in hide_idx_1:
					fg += 1
					continue

				solver_d.net.params['fc1'][0].data[e-fg,...] = solver_t.net.params['fc1'][0].data[e,...]
				solver_d.net.params['fc1'][1].data[e-fg] = solver_t.net.params['fc1'][0].data[e]

		else:
		    solver_d.net.params[p][0].data[...] = solver_t.net.params[p][0].data[...]
		    solver_d.net.params[p][1].data[...] = solver_t.net.params[p][1].data[...]


	return solver_d


def net_surgery(pro, dir_name, lexicon):

	words_s = np.loadtxt('../models/vgg_dictnet_mtoc/dictnet_vgg_labels.txt', dtype='str')
	words_d = np.loadtxt('../vgg_data/' + lexicon, dtype='str')
	idx = dict()

	for e, i in enumerate(words_d):
		if len(np.where(words_s == i)[0]) > 0:
			idx[e] = np.where(words_s == i)[0][0]

	pro.make_prototxt("_fc1_0_fc2_0.prototxt", [4096, 4096, len(words_d)], "0")

	net_s = caffe.Net('../models/vgg_dictnet_mtoc/dictnet_vgg_deploy.prototxt', '../models/vgg_dictnet_mtoc/dictnet_vgg_mtoc.caffemodel', caffe.TEST)
	net_d = caffe.Net(os.path.join(dir_name, "prototxt/0/deploynet_fc1_0_fc2_0.prototxt"), caffe.TEST)

	params_d = net_d.params.keys()


	for p in params_d:
		if p == "fc_class":
			for e in idx:
				try:
					net_d.params[p][0].data[e,...] = net_s.params[p][0].data[idx[e],...]
				except:
					print e, idx[e]
					break
				net_d.params[p][1].data[e] = net_s.params[p][1].data[idx[e]]
		else:
			net_d.params[p][0].data[...] = net_s.params[p][0].data[...]
			net_d.params[p][1].data[...] = net_s.params[p][1].data[...]
	print "end!!"
	net_d.save(os.path.join(dir_name, 'models/0/snap_fc1_0_fc2_0.caffemodel'))

