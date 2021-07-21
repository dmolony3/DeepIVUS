import numpy as np
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import Qt

def IVUS_gating(images, speed, frame_rate):
    """Performs gating of IVUS images"""

    if len(images.shape) == 4:
        images = images[:, :, :, 0]

    num_images = images.shape[0]
    pullback = speed*(num_images-1)/frame_rate # first image is recorded instantly so no time delay

    s0 = np.zeros((num_images-1, 1))
    s1 = np.zeros((num_images-1, 1))

    progress = QProgressDialog()
    progress.setWindowFlags(Qt.Dialog)
    progress.setModal(True)
    progress.setMinimum(0)  
    progress.setMaximum(num_images-1)
    progress.resize(500,100)
    progress.setValue(0)
    progress.setValue(1)
    progress.setValue(0) # trick to make progress bar appear
    progress.setWindowTitle("Computing end diastolic images")
    progress.show()

    for i in range(num_images-1):
        C = normxcorr(images[i, :, :], images[i+1, :, :])
        s0[i] = 1 - np.max(C)
        gradx, grady = np.gradient(images[i, :, :])
        gradmag = abs(np.sqrt(gradx**2 + grady**2))
        s1[i] = -np.sum(gradmag)
        progress.setValue(i)
        if progress.wasCanceled():
            break

    if progress.wasCanceled():
        return None
    progress.close()
    # normalize data
    s0_plus = s0 - np.min(s0)
    s1_plus = s1 - np.min(s1)

    s0_norm = s0_plus/np.sum(s0_plus)
    s1_norm = s1_plus/np.sum(s1_plus)

    alpha=0.25
    s = alpha*s0_norm + (1-alpha)*s1_norm

    # determine Fs (sampling frequency)
    t = np.linspace(0,pullback/speed,num_images)
    Fs = num_images/np.max(t);
    NFFT = int(2**np.ceil(np.log2(np.abs(len(s)))))
    ss = np.fft.fft(s,NFFT, 0)/len(s)
    freq = Fs/2*np.linspace(0,1,NFFT/2+1)

    # in order to return correct amplitude fft must be divided by length of sample
    freq[freq<0.75]=0
    freq[freq>1.66]=0

    ss1 = ss[0:NFFT//2+1]
    ss1[freq == 0]=0

    # determine maximum frequency component of ss
    fm = np.argmax(np.abs(ss1))
    fm = freq[fm]

    # find cutoff frequency
    sigma=0.4
    fc = (1 + sigma)*fm

    # construct low pass kernal (fmax is half of the transducer frame rate)
    fmax = Fs/2
    tau = 25/46
    v = 21/46
    f = ((fc/fmax)*np.sinc((fc*np.arange(1, num_images+1))/fmax))*(tau - v*np.cos(2*np.pi*(np.arange(1, num_images+1)/num_images)))

    # determine low frequency signal 
    s_low = np.convolve(s[:, 0],f)
    s_low = s_low[0:len(s)] # take first half only

    # find first minimum in heartbeat
    hr_frames = int(np.round(Fs/fm)) # heart rate in frames
    idx = np.argmin(s_low[0:hr_frames])
    p = []
    p.append(idx)
    k=0

    while idx < (num_images - hr_frames):
        k =k + 1
        # based on known heart rate seach within 2 frames for local minimum
        # increase fc to look at higher frequencies
        idx2 = idx + np.arange(hr_frames-2, hr_frames+3)
        # find local minimum
        idx2 = idx2[idx2 < num_images -1]
        min_idx = np.argmin(s_low[idx2])
        idx = idx2[min_idx]
        p.append(idx)

    fc = fc + fm
    j = 1
    s_low = np.expand_dims(s_low, 1)

    while fc < fmax:
        # recalculate f with new fc value
        f = ((fc/fmax)*np.sinc((fc*np.arange(1, num_images+1))/fmax))*(tau - v*np.cos(2*np.pi*(np.arange(1, num_images+1)/num_images)))
        # add extra columns to s_low to create surface as in paper
        s_temp = np.expand_dims(np.convolve(s[:,0],f), 1)
        s_low = np.concatenate((s_low, s_temp[0:len(s)]), 1)

        # adjust each previous minimum p(i) to the nearest minimum
        for i in range(len(p)):
            # find index of new lowest p in +/-1 neighbour search
            search_index = np.arange(p[i]-1, p[i]+2)
            search_index = search_index[search_index >= 0]
            search_index = search_index[search_index < len(s)] # <=?
            search_index = np.in1d(np.arange(0, len(s)), search_index)
            # determine index of min value in the specified neighbour range
            min_value = np.argmin(s_low[search_index, j])
            # switch from logical to indexed values
            search_index = np.argwhere(search_index)
            p[i] = search_index[min_value][0]
        # iteratively adjust to the new minimum
        # increase fc to look at higher frequencies
        fc = fc + fm
        j = j + 1

    # normalize each column of s_low
    max_values = np.max(s_low, 0)
    s_low_norm = s_low/np.tile(max_values, [len(s), 1])

    # group images between p(i) and p(i+1)
    # output frames corresponding to each cardiac phase
    HB = []
    for i in range(len(p) - 1):
        HB.append(list(np.arange(p[i], p[i + 1])))

    # identify P cardiac phases (where P is the amount of frames in shortest heartbeat
    P = [len(entry) for entry in HB]
    P = min(P)

    # each column in U corresponds to a cardiac phase (systole, diastole)
    U = np.zeros((len(HB), P))
    for i in range(len(HB)):
        U[i , :] = HB[i][0:P]

    # determine heartbeat period
    t_HB = t[p[1:]] - t[p[:-1]]

    return p

def normxcorr(image1, image2):
    C = np.zeros_like(image1)
    image1_mean = np.mean(image1)
    image2_mean = np.mean(image2)
    image1_std = np.std(image1)
    image2_std = np.std(image2)
    C = np.sum((image1 - image1_mean)*(image2 - image2_mean))/(image1_std*image2_std)
    C = C/(image1.shape[0]*image1.shape[1])
    return C
