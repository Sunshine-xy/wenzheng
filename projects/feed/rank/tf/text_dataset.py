#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# ==============================================================================
#          \file   dataset.py
#        \author   chenghuige  
#          \date   2019-07-26 23:00:24.215922
#   \Description  
# ==============================================================================

  
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys 
import os

import tensorflow as tf 
flags = tf.app.flags
FLAGS = flags.FLAGS

import melt 
import numpy as np

from config import *

class Dataset(melt.tfrecords.Dataset):
  def __init__(self, subset='train'):
    super(Dataset, self).__init__(subset, 
                                  InputDataset=tf.data.TextLineDataset,
                                  use_pyfunc=True)
    
    self.index_addone = int(FLAGS.index_addone)
    self.max_feat_len = FLAGS.max_feat_len

    self.field_id = {}
    self.feat_to_field = {}
    self.load_feature_files()
    self.batch_size = melt.batch_size()

  def load_feature_files(self):
    #   ifs = open(FLAGS.field_file_path, 'r')
    #   cursor = 0
    #   while True:
    #       line = ifs.readline()
    #       if line == '':
    #           break
    #       line = line.rstrip()
    #       self.field_id[line] = cursor
    #       cursor += 1
    #   ifs.close()
      self.field_id = {}
      ifs = open(FLAGS.feat_file_path, 'r')
      while True:
          line = ifs.readline()
          if line == '':
              break
          line = line.rstrip()
          fields = line.split('\t')
          assert len(fields) == 2
          #----------- +1
          #fid = int(fields[1]) - 1 + FLAGS.index_addone
          fid = int(fields[1]) - 1 + self.index_addone
          #fid = int(fields[1]) 

          tokens = fields[0].split('\a')
          if tokens[0] not in self.field_id:
              #----------- +1
              self.field_id[tokens[0]] = len(self.field_id) + self.index_addone
              #self.field_id[tokens[0]] = len(self.field_id) 
          self.feat_to_field[fid] = self.field_id[tokens[0]]
      print('----num fields', len(self.field_id))
      ifs.close()

  def get_feat_id_value(self, fields):
      feat_id = []
      feat_value = []
  
      for i in range(4, len(fields)):
          tokens = fields[i].split(':')
          assert len(tokens) == 2
          f_id = int(tokens[0])
          if f_id in self.feat_to_field:
              f_value = float(tokens[1])
              feat_id.append(f_id)
              feat_value.append(f_value)
  
      return feat_id, feat_value
  
  def get_feat_set(self, fields):
    feat_id = []
    feat_field = []
    feat_value = []

    for i in range(4, len(fields)):
        tokens = fields[i].split(':')
        assert len(tokens) == 2
        # start from 1 so as to let 0 unused
        #----------- +1 as using FLAGS is much slower to set it to self. first..
        #f_id = int(tokens[0]) - 1 + FLAGS.index_addone
        f_id = int(tokens[0]) - 1 + self.index_addone
        f_field = self.feat_to_field[f_id]
        f_value = float(tokens[1])
        feat_id.append(f_id)
        feat_field.append(f_field)
        feat_value.append(f_value)

    return feat_id, feat_field, feat_value


  def make_input_fn(self, feat_list):
      feat_ids = np.zeros((self.batch_size, self.max_feat_len), dtype=np.int64)
      feat_fields = np.zeros((self.batch_size, self.max_feat_len), dtype=np.int64)
      feat_values = np.zeros((self.batch_size, self.max_feat_len), dtype=np.float32)
      labels = np.zeros(self.batch_size, dtype=np.float32)
      ids = [''] * self.batch_size

      cur_max_feat_len = 0
      for bid, feat_line in enumerate(feat_list):
          # python 3 need decode
          fields = feat_line.decode().split('\t')
          #fields = feat_line.split('\t')
          if len(fields) > 4:
              labels[bid] = float(fields[0])
              ids[bid] = '{}\t{}'.format(fields[2], fields[3])
              #feat_id, feat_value = self.get_feat_id_value(fields)
              feat_id, feat_field, feat_value = self.get_feat_set(fields)
              assert len(feat_id) == len(feat_value), "len(feat_id) == len(feat_value) -----------------"
              trunc_len = min(len(feat_id), self.max_feat_len)
              feat_ids[bid, :trunc_len] = feat_id[:trunc_len]
              feat_fields[bid, :trunc_len] = feat_field[:trunc_len]
              feat_values[bid, :trunc_len] = feat_value[:trunc_len]
              cur_max_feat_len = max(cur_max_feat_len, trunc_len)
      
      feat_ids = feat_ids[:, :cur_max_feat_len]
      feat_fields = feat_fields[:, :cur_max_feat_len]
      feat_values = feat_values[:, :cur_max_feat_len]

      #-------do not use np array.. for string
      #ids = np.array(ids)
  
      return feat_ids, feat_fields, feat_values, labels, ids
  
  def parse(self, string_line):
      feat_ids, feat_fields, feat_values, labels, ids  = \
          tf.py_func(self.make_input_fn, [string_line],
                      [tf.int64, tf.int64, tf.float32, tf.float32, tf.string])
    #---for pyfunc you need to set shape.. otherwise first dim unk 
      feat_ids.set_shape((self.batch_size, None))
      feat_fields.set_shape((self.batch_size, None))
      feat_values.set_shape((self.batch_size, None))

      return {'index': feat_ids, 'field': feat_fields, 'value': feat_values, 'id': ids}, labels
  