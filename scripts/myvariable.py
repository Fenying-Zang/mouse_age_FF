# -*- coding: utf-8 -*-
"""
some helpful tools

"""

import pickle
def save_variable(v,filename):
    f=open(filename,'wb')
    pickle.dump(v,f)
    f.close()
    return filename
 
def load_variable(filename):
   f=open(filename,'rb')
   r=pickle.load(f)
   f.close()
   return r

from decimal import Decimal,ROUND_HALF_UP
def smart_round(x,n):
    return str(Decimal(x).quantize(Decimal("0."+"0"*n),rounding=ROUND_HALF_UP))
