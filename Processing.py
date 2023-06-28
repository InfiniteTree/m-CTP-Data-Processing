import numpy as np
import warnings
import math
import csv
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import GridSearchCV
#from sklearn.model_selection import train_test_split


class process:
    Reflect_Info = []
    hsPara = ""
    phenotypePara = ""
    ptsthsParaModel = ""
    ReflectMatrix = []

    ParaMatrix = []
    cur_proportion = 1

    lines = 0
    channels = 0
    samples = 0
    waveStart = 0

    y_pre = []

    ### Need to remap the band intelligently
    # map_num = ("wavelengh" - 400) / ((waveEnd - waveStart) / channels) 
    map_band = {"band430":16, "band445":22, "band500":47, "band510":51,"band531":62, "band550":70, "band570":80, "band635":110, "band670":126, "band680":131, "band700":139, "band705":143, "band750":164,"band780":178, "band800":188, "band900":235,"band970":268}
    
    def __init__(self, reflectInfo, hsParaType, phenotypeParaType, phenotypeParaModelType):
        self.Reflect_Info = reflectInfo
        self.hsPara = hsParaType
        self.phenotypePara = phenotypeParaType
        self.phenotypeParaModel = phenotypeParaModelType

        self.ReflectMatrix = self.Reflect_Info[3]
        self.lines = self.Reflect_Info[0]
        self.channels = self.Reflect_Info[1]
        self.samples = self.Reflect_Info[2]
        self.cur_proportion = self.Reflect_Info[5]
        self.waveStart = int(float(self.Reflect_Info[4][0]))
    
    def calImgSpecMean(self):
        return self.ReflectMatrix.mean(axis=(0,2)) / self.cur_proportion

    # Calculate the relative values the photosynthesis by the design formulas
    def calcHsParas(self):
        self.ReflectMatrix = np.where(self.ReflectMatrix < 0, 0, self.ReflectMatrix)
        self.ReflectMatrix = np.where(self.ReflectMatrix > 1, 1, self.ReflectMatrix)

        match self.hsPara:
            case "NDVI":
                numerator =  self.ReflectMatrix[:,self.map_band["band800"],:] - self.ReflectMatrix[:,self.map_band["band680"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band800"],:] + self.ReflectMatrix[:,self.map_band["band680"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 0  # the denominator is zero, set it as 0
                # All range in [-1, 1], while plant in [0.2, 0.8]
                self.ParaMatrix[self.ParaMatrix < 0] = 0
                self.ParaMatrix[self.ParaMatrix > 1] = 0
                
            case "OSAVI":
                numerator =  (1+0.16) * (self.ReflectMatrix[:,self.map_band["band800"],:] - self.ReflectMatrix[:,self.map_band["band670"],:])
                denominator = self.ReflectMatrix[:,self.map_band["band800"],:] + self.ReflectMatrix[:,self.map_band["band670"],:]+ 0.16
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 0  # the denominator is zero, set it as 0
                
            case "PRI":
                numerator =  self.ReflectMatrix[:,self.map_band["band531"],:] - self.ReflectMatrix[:,self.map_band["band570"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band531"],:] + self.ReflectMatrix[:,self.map_band["band570"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = -0.2  # the denominator is zero, set it as 0
                # All range in [-1, 1], while plant in [-0.2, 0.2]
                self.ParaMatrix[self.ParaMatrix < -0.2] = -0.2
                self.ParaMatrix[self.ParaMatrix > 0.2] = 0.2

            case "MTVI2":
                numerator =  1.5 * (1.2 * (self.ReflectMatrix[:,self.map_band["band800"],:] - self.ReflectMatrix[:,self.map_band["band550"],:]) - 2.5 * (self.ReflectMatrix[:,self.map_band["band670"],:] - self.ReflectMatrix[:,self.map_band["band550"],:]))
                denominator = np.sqrt(((2 * self.ReflectMatrix[:,self.map_band["band800"],:]+1)*2 - (6*self.ReflectMatrix[:,self.map_band["band800"],:]-5*np.sqrt(self.ReflectMatrix[:,self.map_band["band670"],:]))-0.5))
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 0  # the denominator is zero, set it as 0
            
            case "SR":
                numerator =  self.ReflectMatrix[:,self.map_band["band800"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band680"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 2  # the denominator is zero, set it as 0
                self.ParaMatrix[self.ParaMatrix < 2] = 2
                self.ParaMatrix[self.ParaMatrix > 8] = 8
            
            case "DVI":
                var_1 =  self.ReflectMatrix[:,self.map_band["band800"],:]
                var_2 = self.ReflectMatrix[:,self.map_band["band680"],:]
                self.ParaMatrix = var_1 - var_2
                
            case "SIPI":
                numerator =  self.ReflectMatrix[:,self.map_band["band800"],:] - self.ReflectMatrix[:,self.map_band["band445"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band800"],:] + self.ReflectMatrix[:,self.map_band["band680"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 0  # the denominator is zero, set it as 0
                self.ParaMatrix[self.ParaMatrix < 0] = 0
                self.ParaMatrix[self.ParaMatrix > 2] = 2

            case "PSRI":
                numerator =  self.ReflectMatrix[:,self.map_band["band680"],:] - self.ReflectMatrix[:,self.map_band["band500"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band750"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = -1  # the denominator is zero, set it as 0
                self.ParaMatrix[self.ParaMatrix < -1] = -1
                self.ParaMatrix[self.ParaMatrix > 1] = 1

            case "CRI1":
                denominator_1 = self.ReflectMatrix[:,self.map_band["band510"],:]
                denominator_2 = self.ReflectMatrix[:,self.map_band["band550"],:]
                denominator_1[denominator_1 == 0] = 0  # Avoid the denominator is zero, set it as 1 
                denominator_2[denominator_2 == 0] = 0  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = 1/denominator_1 - 1/denominator_2
                self.ParaMatrix[self.ParaMatrix < 0] = 0 
                self.ParaMatrix[self.ParaMatrix > 15] = 0
            
            case "CRI2":
                denominator_1 = self.ReflectMatrix[:,self.map_band["band510"],:]
                denominator_2 = self.ReflectMatrix[:,self.map_band["band700"],:]
                denominator_1[denominator_1 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                denominator_2[denominator_2 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = 1/denominator_1 - 1/denominator_2
                self.ParaMatrix[self.ParaMatrix < 0] = 0 
                self.ParaMatrix[self.ParaMatrix > 15] = 15


            case "ARI1":
                denominator_1 = self.ReflectMatrix[:,self.map_band["band550"],:]
                denominator_2 = self.ReflectMatrix[:,self.map_band["band700"],:]
                denominator_1[denominator_1 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                denominator_2[denominator_2 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = 1/denominator_1 - 1/denominator_2
                self.ParaMatrix[self.ParaMatrix < 0] = 0 
                self.ParaMatrix[self.ParaMatrix > 0.2] = 0.2

            case "ARI2":
                denominator_1 = self.ReflectMatrix[:,self.map_band["band550"],:]
                denominator_2 = self.ReflectMatrix[:,self.map_band["band700"],:]
                denominator_1[denominator_1 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                denominator_2[denominator_2 <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = self.ReflectMatrix[:,self.map_band["band800"],:] * (1/denominator_1 - 1/denominator_2)
                self.ParaMatrix[self.ParaMatrix < 0] = 0 
                self.ParaMatrix[self.ParaMatrix > 0.2] = 0.2

            case "WBI":
                numerator =  self.ReflectMatrix[:,self.map_band["band900"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band970"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 0  # the denominator is zero, set it as 0
                # plant in [0.8, 1.2]
                self.ParaMatrix[self.ParaMatrix <= 0.8] = 0.8
                self.ParaMatrix[self.ParaMatrix >= 1.2] = 1.2

            # Bugs remain in PSSRa and PSSRb, which is caused by the raw data of band680/band635 
            # (reflectance is approximately zero and make the calculation result too large)
            case "PSSRa":
                numerator =  self.ReflectMatrix[:,self.map_band["band800"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band680"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 2  # the denominator is zero, set it as 0
                self.ParaMatrix[self.ParaMatrix < 2] = 2
                self.ParaMatrix[self.ParaMatrix > 8] = 8
            
            case "PSSRb":
                numerator =  self.ReflectMatrix[:,self.map_band["band800"],:]
                denominator = self.ReflectMatrix[:,self.map_band["band635"],:]
                denominator[denominator <= 0] = 1  # Avoid the denominator is zero, set it as 1 
                self.ParaMatrix = numerator / denominator
                self.ParaMatrix[denominator == 0] = 2  # the denominator is zero, set it as 0
                self.ParaMatrix[self.ParaMatrix < 2] = 2
                self.ParaMatrix[self.ParaMatrix > 8] = 8

            # Self defined formular
            case "user-defined":
                print("ok")
        
        if np.any(self.ParaMatrix > 10):
            print("Yes >10")
        
        if np.any(self.ParaMatrix < -10):
            print("Yes <10")

        #self.ParaMatrix[self.ParaMatrix < -1] = -1
        #self.ParaMatrix[self.ParaMatrix > 1] = 1

        #print(self.ParaMatrix)

    def draw_pseudoColorImg(self, flag):
        #print(self.ParaMatrix)
        fig, ax = plt.subplots(figsize=(6, 8))
        #print(self.hsPara)
        match self.hsPara:
            case "NDVI":
                im = ax.imshow(self.ParaMatrix, cmap='gray',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on NDVI", y=1.05)
            case "OSAVI":
                im = ax.imshow(self.ParaMatrix, cmap='viridis',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on OSAVI", y=1.05)
            case "PSSRa":
                im = ax.imshow(self.ParaMatrix, cmap='spring',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on PSSRa", y=1.05)
            case "PSSRb":
                im = ax.imshow(self.ParaMatrix, cmap='summer',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on PSSRb", y=1.05)
            case "PRI":
                im = ax.imshow(self.ParaMatrix, cmap='magma',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on PRI", y=1.05)
            case "MTVI2":
                im = ax.imshow(self.ParaMatrix, cmap='hot',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on MTVI2", y=1.05)

            case "SR":
                im = ax.imshow(self.ParaMatrix, cmap='gray',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on SR", y=1.05)
            case "DVI":
                im = ax.imshow(self.ParaMatrix, cmap='viridis',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on DVI", y=1.05)
            case "SIPI":
                im = ax.imshow(self.ParaMatrix, cmap='spring',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on SIPI", y=1.05)
            case "PSRI":
                im = ax.imshow(self.ParaMatrix, cmap='summer',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on PSRI", y=1.05)
            case "CRI1":
                im = ax.imshow(self.ParaMatrix, cmap='magma',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on CRI1", y=1.05)
            case "CRI2":
                im = ax.imshow(self.ParaMatrix, cmap='hot',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on CRI2", y=1.05)
            case "ARI1":
                im = ax.imshow(self.ParaMatrix, cmap='summer',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on ARI1", y=1.05)
            case "ARI2":
                im = ax.imshow(self.ParaMatrix, cmap='magma',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on ARI2", y=1.05)
            case "WBI":
                im = ax.imshow(self.ParaMatrix, cmap='hot',interpolation='nearest')
                ax.set_title("Pseudo_Color Map of the Relative Values on WBI", y=1.05)

        cbar = fig.colorbar(im)
        if flag == "Save": 
            plt.savefig("figures/test/process/" + self.hsPara + ".jpg")
            plt.close()

        if flag == "View": # Consider to just load the figure here!!!!!!!!!
            plt.show()

    # Machine learning prediction
    def CalcPhenotypeParas(self, index):
        # Fault Value Detection
            # Get the remaining parameters by using the trained model to predict
            if self.phenotypeParaModel == "PLSR":
                data = pd.read_csv("model/LearningData/TrainData.csv")
                #print("Dataset of Train Model loaded...")
                train_x = data.drop(['SPAD',"A1200", "N", "Ca", "Cb"],axis=1)
                #train_y = data[['SPAD',"A1200", "N", "Ca", "Cb"]].copy()
                train_y = data[[self.phenotypePara]]

                train_x = pd.DataFrame(train_x, dtype='float32')
                train_y = pd.DataFrame(train_y, dtype='float32')

                # pls_param_grid = {'n_components': list(range(10,20))}
                # Train the data
                pls_param_grid = {'n_components':[10]}  

                warnings.filterwarnings('ignore', category=UserWarning)
                pls = GridSearchCV(PLSRegression(), param_grid=pls_param_grid,scoring='r2',cv=10)
                pls.fit(train_x, train_y)

                # test_x stores the raw data for one pixel; y_pre stores the dealt results for all pixels
                test_x = self.ReflectMatrix[index//self.samples,6:-16,index%self.samples] # The data set of the train model only contains HS in parts of wavelength range
                test_x = pd.Series(test_x, dtype='float32')
                test_x = test_x.to_frame().T
                self.y_pre.append(pls.predict(test_x))

    # export file 1 to store the spectra data  
    def HyperspectraCurve(self, HSI_info, proportion):
        # Show the spectra curve
        wavelengths = HSI_info[4]
        lines = HSI_info[0]
        channels= HSI_info[1]
        samples = HSI_info[2]
        HSI = HSI_info[3]
        remainRow = []

        spec_mean = self.calImgSpecMean(HSI,proportion)
        x = [float(num) for num in wavelengths] # change str to float
        y = np.array(spec_mean)
        plt.xlabel("Wavelength(nm)")
        plt.ylabel("Hyperspectral Luminance")
        plt.title("The Average Hyperspectral of the Light Blades")
        plt.plot(x,y,c='lightcoral',label='Curve_poly_Fit')
        plt.savefig("Results/Hyperspec_curve.jpg")
        remainRow = spec_mean
            
        #plt.show()

        # Export the data of hyperspectra curve into the local .csv
        FirstRow = wavelengths
        
        curveFile = "Results/Hyperspectra_Avg_curve.csv"
        with open(curveFile,"w",newline='') as f:
            writer = csv.writer(f)
            # Write the first row
            writer.writerow(FirstRow)
            # Write the remaining rows
            writer.writerow(remainRow)

        return curveFile

    # export file to store the Parameters of Phenotype in terms of the single plot
    def exportPhenotypeParas(self, Readfilename):

        FirstRow = ["NDVI", "OSAVI", "PSSRa", "PSSRb", "RPI", "MTVI2", "SPAD","A1200", "N", "Ca", "Cb"]
        avg_flag = 1
        # Read the reflectance file and calculate the Phenotype parameters
        with open(Readfilename,"r",newline='') as f:
            contents = f.readlines()
            reflectances = contents[1].split(",")
            #print(reflectances)
            reflectances = [float(num) for num in reflectances] # change str to float
            PhenotypeParas= getPhenotypeParas(reflectances, avg_flag)

        # Export the results
        with open("Results/Phenotype_Paras_withReflectance.csv","w",newline='') as f:
            writer = csv.writer(f)
            writer.writerow(FirstRow)
            writer.writerow(PhenotypeParas)

        return

    # export file to store the Parameters of Phenotype in terms of the single pixel
    def exportPhenotypeParas_eachPixel(self, HSI_info,reflectanceMatrix):
        lines = HSI_info[0]
        channels= HSI_info[1]
        samples = HSI_info[2]

        FirstRow = ["Loc","NDVI", "OSAVI", "PSSRa", "PSSRb", "RPI", "MTVI2"]

        avg_flag = 0
        PhenotypeParas= []

        # Export the results
        with open("Results/Phenotype_Paras_eachPixel.csv","w",newline='') as f:
            writer = csv.writer(f)
            writer.writerow(FirstRow)
            for i in range(samples*lines):
                row = i//samples
                col = i%samples
                PhenotypeParas = self.getPhenotypeParas(reflectanceMatrix[row,:,col], avg_flag)
                writer.writerow([(row,col)]+PhenotypeParas)
