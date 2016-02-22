import pickle
import csv

input_pkl_file = "HLT_Fit_Run258425-260627_Tot10_fit.pkl"
output_csv_file = "HLT_Fit_Run258425-260627_Tot10_fit.csv"

fits_dict = pickle.load(open(input_pkl_file,"rb"))

output = open(output_csv_file,'w')
output_writer = csv.writer(output)

output_writer.writerow(["path name","fit function", "X0", "X1", "X2", "X3", "sigma", "meanraw", "X0err", "X1err", "X2err", "X3err", "ChiSqr"])

for trigger in fits_dict:
    row = []
    row.append(trigger)
    for param in fits_dict[trigger]: row.append(param)
    output_writer.writerow(row)

output.close()
    
