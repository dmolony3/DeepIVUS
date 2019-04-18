import xml.etree.ElementTree as ET

def splitxy(points):
    """Splits comma separated points into separate x and y lists"""
    pointsX = []
    pointsY = []
    for i in range(0, len(points)):
        pointsX.append(map(lambda x:int(x.split(',')[0]), points[i]))
        pointsY.append(map(lambda x:int(x.split(',')[1]), points[i]))
    return pointsX, pointsY

def read(path, frames=[]):
    tree = ET.parse(path)
    root = tree.getroot()
    print(root.tag)
    root.attrib
    print(root[0].text)
    lumen_points = []
    vessel_points = []
    stent_points = []
    no_points = []
    framelist = []
    lumen={}
    vessel={}
    stent={}
    for child in root:
        # use text to see the values in the tags
        #print(child.tag, child.text)
        for imageState in child.iter('ImageState'):
            xdim = imageState.find('Xdim').text
            ydim = imageState.find('Ydim').text
            zdim = imageState.find('NumberOfFrames').text
            if not frames:
                frames=range(int(zdim))
        for imageCalibration in child.iter('ImageCalibration'):
            xres = imageCalibration.find('XCalibration').text
            yres = imageCalibration.find('YCalibration').text
            pullbackSpeed = imageCalibration.find('PullbackSpeed').text
            #frameTime = imageCalibration.find('FrameTimeInMs').text
        for frameState in child.iter('FrameState'):
            xOffSet = frameState.find('Xoffset').text
            yOffSet = frameState.find('Yoffset').text
            fm = frameState.find('Fm').iter('Num')
            for frame in child.iter('Fm'):
                frameNo = int(frame.find('Num').text)
                print('Reading frame no {}'.format(frameNo))
                # iterate through the frame and identify the contour
                lumen_subpoints = []
                vessel_subpoints = []
                stent_subpoints = []
                if frameNo in frames:
                    for pts in frame.iter('Ctr'):
                        framelist.append(frameNo)
                        for child in pts:
                            if child.tag =='Type':
                                if child.text == 'L':
                                    contour = 'L'
                                elif child.text == 'V':
                                    contour = 'V'
                                elif child.text == 'S':
                                    contour= 'S'
                            if child.tag == 'Npts':
                                no_points.append(child.text)
                        # add each point
                            elif child.tag == 'p':
                                if contour == 'L':
                                    lumen_subpoints.append(child.text)
                                elif contour == 'V':
                                    vessel_subpoints.append(child.text)
                                elif contour == 'S':
                                    stent_subpoints.append(child.text)

                    lumen_points.append(lumen_subpoints)
                    vessel_points.append(vessel_subpoints)
                    stent_points.append(stent_subpoints)
                    lumen[frameNo] = lumen_subpoints
                    vessel[frameNo] = vessel_subpoints
                    stent[frameNo] = stent_subpoints


    Lx, Ly = splitxy(lumen_points)
    Vx, Vy = splitxy(vessel_points)
    Sx, Sy = splitxy(stent_points)
    pointsY = []

    # return unique frames as we have entry for each inner and outer contour
    framelist = list(sorted(set(map(int, framelist))))

    print((xdim, ydim, zdim))
    print((xres, yres))

    return (Lx, Ly), (Vx, Vy), (Sx, Sy), [xres, yres], framelist
