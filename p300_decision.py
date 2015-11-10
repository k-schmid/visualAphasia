import random
from numpy import *
import numpy.ma as ma


class decider(object):
    
    def __init__(self):
        self.__allowed_strategy = ['rowcol', 'individual']
        self.__default_strategy = 'rowcol'
       
        self.strategy = self.__std_strategy = self.__default_strategy
        self.mask = self.__std_mask = ones([6,6], dtype=int)
        self.num_iter = self.__std_num_iter = 10
        self.num_subt_per_iter = self.__std_num_subt_per_iter = 6
        self.__resize_scoring_mat()
    
    def reset(self):
        self.strategy = self.__std_strategy
        self.mask = self.__std_mask
        self.num_iter = self.__std_num_iter
        self.num_subt_per_iter = self.__std_num_subt_per_iter
        self.__resize_scoring_mat()
        
    
    def set(self, param_set):
        for param in enumerate(param_set):
            if param[1] == 'num_iter':
                self.num_iter = param_set[param[1]]
            elif param[1] == 'num_subt_per_iter':
                self.num_subt_per_iter = param_set[param[1]]           
            elif param[1] == 'strategy':
                if param_set[param[1]] in self.__allowed_strategy:
                    self.strategy = param_set[param[1]]
                else:
                    self.strategy = self.__default_strategy
                    print "Error: '%s' stategy not implemented. Using '%s'" % (strategy, self.__default_strategy)            
            elif param[1] == 'mask':
                self.mask = array(param_set[param[1]])
            else:
                print "Error: parameter %s is not in parameter set" % param[1]
        self.__resize_scoring_mat()

    def give_strategies(self):
        return self.__allowed_strategy
    
	# call every time scores are received
	# 	sco_val = [score, [image indexes]]
	
    def add_score(self, sco_val):
        clas_sco = sco_val[0][0]
        clas_id = sco_val[1]     
        
        if self.strategy == 'rowcol':
            clas_id = self.__get_ind(clas_id)
        
        for id in range(len(clas_id)):
            self.scoring_mat[clas_id[id], where(self.scoring_mat[clas_id[id],]== inf)[0][0]] = array(clas_sco)
        print self.scoring_mat
	
    def query_winner(self):
        mask = zeros(self.scoring_mat.shape)
        mask[where(self.scoring_mat == inf)] = 1
        if self.strategy == 'rowcol':
            val_id = concatenate((self.mask.sum(1).nonzero()[0], self.mask.sum(0).nonzero()[0]+self.mask.shape[0]))
            val_mas = ones(sum(self.mask.shape)).astype(bool)
            val_mas[val_id] = False
        else:
            val_mas = ~ self.mask.ravel().astype(bool)
        
        msk_scor = ma.MaskedArray(self.scoring_mat, mask)
        msk_scor = ma.MaskedArray(ma.median(msk_scor, axis=1), val_mas)

        print self.mask        
        if self.strategy == 'rowcol':
            row_win = msk_scor[:self.mask.shape[0]].argmin()
            col_win = msk_scor[self.mask.shape[0]:].argmin()
            return row_win * self.mask.shape[0] + col_win
        else:
            return msk_scor.argmin()
        
    def __get_ind(self, clas_id):
        if all(diff(sort(clas_id))-1):
            # col
            return [int(sort(clas_id)[0] + self.mask.shape[0])]
        else:
            # row
            return [int(clas_id[0]/self.mask.shape[1])]
    
    def __resize_scoring_mat(self):
        if self.strategy == "rowcol":
            self.scoring_mat = ones((sum(self.mask.shape),self.num_iter/2))*inf
        elif self.strategy == "individual":
            self.scoring_mat = ones((self.mask.size,self.num_iter))*inf    

    
