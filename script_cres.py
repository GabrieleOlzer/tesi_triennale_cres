import numpy as np
import subprocess
import gzip
import shutil
import os
import xml.etree.ElementTree as ET
from genevapylib.CombineAnalyzerFiles import getcodefromfile
import math as m
import psutil
import sys
import yaml
from yaml import load

#-------------------------------------------------------------------------------------------------------------------------------------------------

#Direct copy without unzipping		
def copy_last_n_lines_direct(infile, outfile, n):
   """Copies the last n lines of a file and appends them to another file"""
   
   with gzip.open(infile, 'rt') as f_in:
      lines = f_in.readlines()
      last_n_lines = lines[-n:]
	
   with gzip.open(outfile, 'at') as f_out:
      f_out.writelines(last_n_lines)
      
   
def import_xml (analyzer_file_xml):

	tree = ET.parse(analyzer_file_xml)
	root = tree.getroot()
        #print('#point2: RAM Used (GB):', psutil.Process().memory_info().rss/1000000000.)
# Note: the filestem here refers to the previous title
	filestem = root.findall("./Summary/Title")[0].text
	rate = {}
	hist = {}
# load analyzer files
	code = root.findall("./AnalyzerOutput")[0].text
	code = getcodefromfile(code)
        #print('#point2: code size (GB):', sys.getsizeof(code)/1000000000.)
	codelist = code.split('\n')
	if(len(codelist) > 100):
	   step = 100
	else:
	   step = len(codelist)
        for i in range(int(m.floor(len(codelist)/step)-1)):
	   codei = '\n'.join(codelist[:step])
	   exec(codei)
	   #print('#point'+str(2+i)+': RAM Used (GB):', psutil.Process().memory_info().rss/1000000000.) 
	   #print('#point'+str(2+i)+': hist size (GB):', sys.getsizeof(hist)/1000000000.)
	   #print('#point'+str(2+i)+': rate size (GB):', sys.getsizeof(rate)/1000000000.)
	   del codelist[:step]
	codei = '\n'.join(codelist)
	exec(codei)
	del codelist
	
	return hist	

def chi_squared_test(values_1, values_2, errors_1, errors_2):
   """Performs chi squared test between two distributions"""
	
   dof = len(values_1)-1  #number of degrees of freedom
   var = 0.0  #Variable to store the sum of contribuitons to the chi value (not yet divided by the number of dof)
   for i in range(dof):
      num = pow(values_1[i] - values_2[i], 2)
      den = pow(errors_1[i], 2) + pow(errors_2[i], 2)
      if (den == 0):
         var += 0.
      else:
         var += num/den
   chi_value = var/dof
  
   return chi_value		
	
#-----------------------------------------------------------------------------------------------------------------------------------------------------

#Output directory
directory = raw_input("Insert name of the output directory: ")
#create_directory = subprocess.check_output(["mkdir", directory])

resampled_data = directory + "/resampled_data"
#create_resampled_data = subprocess.check_output(["mkdir", resampled_data])

#Getting resampling parameters from user input
jet_radius = raw_input("Jet radius: ")
jr = "--jetradius=" + jet_radius
jet_pt = raw_input("Jet pt: ")
jpt = "--jetpt=" + jet_pt
max_cell_size = raw_input("Max cell size: ")
max_cs = "--max-cell-size=" + max_cell_size

#Analyzing and resampling all the .lhef files in the current working directory
working_dir = os.getcwd()
ext = '.lhe.gz'
for data_file in os.listdir(working_dir):
   if data_file.endswith(ext):
      input_file = data_file
      
      #Analyze the original file
      analyze_or = subprocess.check_output(["../geneva-cpp-lhef-analyze", "--infile", input_file, "--option-file", "input.yml", "--enforce-lhef-options", "off", "--outpath", directory])

      #Cell resampling
      cell_resampling = subprocess.check_output(["cres", "--jetalgorithm=anti-kt", jr, jpt, "--compression=gzip", max_cs, "-o", resampled_data, input_file])
      resampled_file = resampled_data + "/" + input_file

      #Copy comment lines to resampled file
      copy_last_n_lines_direct(input_file, resampled_file, 45)

      #Analyze the resampled file
      analyze = subprocess.check_output(["../geneva-cpp-lhef-analyze", "--infile", resampled_file, "--option-file", "input.yml", "--enforce-lhef-options", "off", "--outpath", resampled_data])
      

#Combining all original .xml files 
combine_originals = '../geneva-combine-plots'+" "+directory+'/*.xml --keep --outfile'+" "+directory+'/merged_originals.xml'
os.system(combine_originals)

#Combining all resampled .xml files 
combine_resampled = '../geneva-combine-plots'+" "+resampled_data+'/*.xml --keep --outfile'+" "+resampled_data+'/merged_resampled.xml'
os.system(combine_resampled)

#Importing histograms of distributions
stem_or ="merged_originals"
stem_res ="merged_resampled"
or_path = directory + "/" + stem_or + ".xml"
res_path = resampled_data + "/" + stem_res + ".xml"
hist_original = import_xml(or_path)
hist_resampled = import_xml(res_path)

#Plot comparing original and resampled distributions
plot_dir = resampled_data+"/plot"
plot = subprocess.check_output(['../../../scripts/MakePlots.py', or_path, res_path, '-p -o',  plot_dir,  '-a', '0', '-w'])

#The following portion of code performs a test of campatibility between the original and resampled distributions  
#Getting the observables for the comparison from the configuration file
yaml_file = open("config.yml", 'r')
observables = yaml.load(yaml_file)
yaml_file.close()
original_obs = []
resampled_obs = []
original_err = []
resampled_err = []

#Creating merged lists for observables and errors for both the original and resampled data
for key, obs in observables.items():

   original_obs += hist_original[stem_or, obs, "central", "value"]
   resampled_obs += hist_resampled[stem_res, obs, "central", "value"]
   original_err += hist_original[stem_or, obs, "central", "error"]
   resampled_err += hist_resampled[stem_res, obs, "central", "error"]

chi_squared = chi_squared_test(original_obs, resampled_obs, original_err, resampled_err)
print("Chi value: "+str(chi_squared))

file_chi_value = directory+"/"+directory+"_chi_value.txt"
f = open(file_chi_value, "w")
f.write("Chi value: "+str(chi_squared))
f.close()









