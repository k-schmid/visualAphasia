import random
from numpy import *


class sequenceGenerator(object):
    
    def __init__(self):
        self.__allowed_strategy = ['rowcol', 'individual', 'load']
        self.__default_strategy = 'rowcol'

        self.strip_empty_boxes = self.__std_strip_empty_boxes = False       
        self.strategy = self.__default_strategy
        self.mask = self.__std_mask = ones([6,6], dtype=int)
        self.num_iter = self.__std_num_iter = 10
        self.num_subt_per_iter = self.__std_num_subt_per_iter = 6
        self.filename = self.__std_filename = ''
        self.rowcol_dist = self.__std_rowcol_dist = 2
    
    def reset(self):
        """
        Reset all variables to the defaults
        """
        self.strategy = self.__default_strategy
        self.mask = self.__std_mask
        self.num_iter = self.__std_num_iter
        self.num_subt_per_iter = self.__std_num_subt_per_iter
        self.filename = self.__std_filename
        self.rowcol_dist = self.__std_rowcol_dist
        self.strip_empty_boxes = self.__std_strip_empty_boxes
    
    def set(self, param_set):
        """
        Function to set parameters. Use this function rather than operating on
        on the variables directly, as it ensures variable types and does error 
        checking.
        """
        for param in enumerate(param_set):
            if param[1] == 'num_iter':
                self.num_iter = param_set[param[1]]
            elif param[1] == 'strip_empty_boxes':
                self.strip_empty_boxes = param_set[param[1]]
            elif param[1] == 'num_subt_per_iter':
                self.num_subt_per_iter = param_set[param[1]]
            elif param[1] == 'rowcol_dist':
                self.rowcol_dist = param_set[param[1]]                
            elif param[1] == 'strategy':
                if param_set[param[1]] in self.__allowed_strategy:
                    self.strategy = param_set[param[1]]
                else:
                    self.strategy = self.__default_strategy
                    print "Error: '%s' stategy not implemented. Using '%s'" % (strategy, self.__default_strategy)            
            elif param[1] == 'mask':
                self.mask = array(param_set[param[1]])
            elif param[1] == 'filename':
                self.filename = param_set[param[1]]
            else:
                print "Error: parameter %s is not in parameter set" % param[1]

    def generate(self, params={}):
        """
        Generate a sequence based on the parameters. 
        """
        self.set(params)
        if self.strategy == 'load':
            if len(self.filename) == 0:
                print "Error: no filename is given. Using default mode %" % self.__default_strategy
                self.strategy = self.__default_strategy
            else:
                return self.__load_file(self.filename, self.num_iter*self.num_subt_per_iter, self.mask.size/self.num_subt_per_iter)
        if self.strategy == 'rowcol':
            return self.__row_col_seq()
        elif self.strategy == 'individual':
            return self.__indiv_seq()

    def give_strategies(self):
        return self.__allowed_strategy
    
    def __indiv_seq(self):
        val_id = where(self.mask.flatten()==1)[0]
        acc_occ = zeros((self.mask.size,self.mask.size))
        
    def __row_col_seq(self):
        # by definition: rows are first ids, then cols
        if  not self.num_iter%2 == 0:
            self.set({'num_iter':self.num_iter+1})
            print "Warning: in rowcol mode, num_iter should be even. Now set to %i" % self.num_iter
        val_id = concatenate((self.mask.sum(1).nonzero()[0], self.mask.sum(0).nonzero()[0]+self.mask.shape[0]))
        seq_list = zeros([self.num_iter*len(val_id)/2], dtype=int)

        return self.__convert_to_mat(self.__recur_add_iter(val_id, seq_list))
        
    def __convert_to_mat(self, seq):
        conv_mat = arange(self.mask.size).reshape(self.mask.shape)
        ret_seq = [];
        ret_str = [];
        
        for i in range(len(seq)):
            if seq[i] < self.mask.shape[0]:
                to_app = conv_mat[seq[i],:].tolist()
                ret_seq.append(to_app)
                ret_str.append([to_app[x] for x in range(len(to_app)) if self.mask[seq[i]][x] == 1])
            else:
                to_app = conv_mat[:,seq[i]-self.mask.shape[0]].tolist()
                ret_seq.append(to_app)
                ret_str.append([to_app[x] for x in range(len(to_app)) if self.mask[x][seq[i]-self.mask.shape[0]] == 1])

        
                
        if self.strip_empty_boxes:
            return ret_str
        else:
            return ret_seq
    
    def __recur_add_iter(self, val_id, seq, depth=0):
        if depth == self.num_iter/2:
            return seq
        
        str_id = depth*len(val_id)
        end_id = (depth+1)*len(val_id)
        
        correct = False
        random.shuffle(val_id)
        while depth > 0 and not correct:
            random.shuffle(val_id)
            correct = True
            for ch_id in range(self.rowcol_dist):
                if val_id[ch_id] in seq[str_id-(self.rowcol_dist+1)+ch_id:str_id]:
                    correct = False
            
        seq[str_id:end_id] = val_id
        return self.__recur_add_iter(val_id, seq, depth+1)

    def __load_file(self, filename, subtrial_count, highlight_count):
        subtrial_count = int(subtrial_count)
        highlight_count = int(highlight_count)
        fp = open(filename, "r")
        data = fp.readlines()
        fp.close()

        lines = []
        totalvalues = 0
        for d in data:
            dt = d[:-1] # remove the \n
            vals = dt.split(',')
            print len(vals)
            print (subtrial_count * highlight_count)
            if len(vals) != (subtrial_count * highlight_count):
                print "Error: line %d has incorrect number of values!" % (len(lines)+1)
                return None
            totalvalues += len(vals)
            lines.append(vals)

        print "(Loading highlights for %d trials)" % (len(lines))

        entries = []

        for i in range(len(lines)):
            entries.append([])
            for j in range(subtrial_count):
                entries[i].append([])
                for k in range(highlight_count):
                    entries[i][j].append(int(lines[i][(j*highlight_count)+k]))

        return entries

    def save(filename, trial_count, subtrial_count, highlight_count):
        subtrial_count = int(subtrial_count)
        highlight_count = int(highlight_count)
        s = ""
        for i in range(trial_count):
            for j in range(subtrial_count):
                for k in range(highlight_count):
                    s+=str(random.randint(0, 30))+","
            s = s[:-1]
            s += '\n'
        fp = open(filename, "w")
        fp.write(s)
        fp.close()
