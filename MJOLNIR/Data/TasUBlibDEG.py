import numpy as np

def cosd(x):
    return np.cos(np.deg2rad(x))

def sind(x):
    return np.sin(np.deg2rad(x))

def tand(x):
    return np.tan(np.deg2rad(x))

def arccosd(x):
    return np.rad2deg(np.arccos(x))

def arcsind(x):
    return np.rad2deg(np.arcsin(x))

def arctan2d(y,x):
    return np.rad2deg(np.arctan2(y,x))

factorsqrtEK = 0.694692

def uFromAngles(om,sgu,sgl):
    return np.array([cosd(om)*cosd(sgl),-sind(om)*cosd(sgu)+cosd(om)*sind(sgl)*sind(sgu),
                      sind(om)*sind(sgu)+cosd(om)*sind(sgl)*cosd(sgu)]).T
    
    
def calcUBFromAngles(B, om, sgu, sgl):
    N = np.array([[1.0,0,0],[0,cosd(sgu),-sind(sgu)],[0,sind(sgu),cosd(sgu)]])
    M = np.array([[cosd(sgl),0,sind(sgl)],[0,1,0],[-sind(sgl),0,cosd(sgl)]])    
    OM= np.array([[cosd(om),-sind(om),0],[sind(om),cosd(om),0],[0,0,1]])
    
    UB = np.dot(OM,M)
    UB = np.dot(UB,N)
    UB = np.dot(UB,B)

    return UB  

def calculateBMatrix(cell):
    [a1,a2,a3,b1,b2,b3,alpha1,alpha2,alpha3,beta1,beta2,beta3] = cell
    
    B = np.array([[b1,b2*cosd(beta3),b3*cosd(beta2)],
              [0,b2*sind(beta3),-b3*sind(beta2)*cosd(alpha1)],
              [0,0,b3]]) # 2*np.pi/a3
    return B

def matFromTwoVectors(v1,v2):
    a1 = v1/np.linalg.norm(v1)
    a2 = v2/np.linalg.norm(v2)
    a3 = np.cross(a1,a2)
    a3/=np.linalg.norm(a3)
    a2 = np.cross(a1,a3)
    return np.array([a1,a2,a3])


def calcTheta(ki,kf,stt):
    return arctan2d(np.abs(ki) - np.abs(kf) * cosd(stt), #rtan
              np.abs(kf) * sind(stt));
    
def calcTasUVectorFromAngles(r):
    A3 = r[3]
    A4 = r[4]
    ss = np.sign(A4) # Scattering sense
    stt = np.abs(A4) # Sample 2theta
    Ei = r[7]
    Ef = r[8]
    ki = np.sqrt(Ei)*factorsqrtEK
    kf = np.sqrt(Ef)*factorsqrtEK
    sgu = r[5]
    sgl = r[6]
    
    theta = calcTheta(ki, kf, stt)
    try:
        om = A3-ss*theta
    except:
        om = A3.reshape(-1,1,1)-ss*theta
    return uFromAngles(om,sgu,sgl)
  
def calcTasUBFromTwoReflections(cell, r1, r2):
    B = calculateBMatrix(cell)
    R1 = np.array(r1[:3])
    R2 = np.array(r2[:3])
    h1 = np.dot(B,R1)
    h2 = np.dot(B,R2)
    
    HT = matFromTwoVectors(h1, h2)
    u1 = calcTasUVectorFromAngles(r1)
    u2 = calcTasUVectorFromAngles(r2)
    
    UT = matFromTwoVectors(u1, u2)
    HTT = HT.T
    
    U = np.dot(UT,HTT)
    UB = np.dot(U,B)
    return UB
    
def tasReflectionToQC(qe,UB):
    qe = qe[:3]
    return np.dot(UB,qe)

def buildTVMatrix(U1V,U2V):
    U1V /=np.linalg.norm(U1V)
    U2V /=np.linalg.norm(U2V)
    T3V = np.cross(U1V.T, U2V.T).T
    
    return np.array([U1V,U2V,T3V])

def buildRMatrix(UB, planeNormal, qe):
    U1V = tasReflectionToQC(qe,UB)
    U1V/=np.linalg.norm(U1V)
    U2V = np.cross(planeNormal.T, U1V.T).T
    if np.linalg.norm(U2V)<0.001:
        raise AttributeError('Calculate length of U2V too small ({})'.format(U2V))
    
    TV = buildTVMatrix(U1V, U2V)
    TVinv = np.linalg.inv(TV)
    return TVinv

def calcTasQAngles(UB,planeNormal,ss,A3Off,qe):
    R = buildRMatrix(UB,planeNormal,qe)
    cossgl = np.sqrt(R[0,0]*R[0,0]+R[1,0]*R[1,0])
    sgl = ss*arctan2d(-R[2,0],cossgl)
    om = arctan2d(R[1,0]/cossgl, R[0,0]/cossgl)
    sgu = arctan2d(R[2,1]/cossgl, R[2,2]/cossgl)
    
    QC = tasReflectionToQC(qe, UB)
    q = np.linalg.norm(QC);
    
    Ei = qe[3]
    Ef = qe[4]
    
    ki = np.sqrt(Ei)*factorsqrtEK
    kf = np.sqrt(Ef)*factorsqrtEK
    
    cos2t =(ki**2 + kf**2 - q**2) / (2. * np.abs(ki) * np.abs(kf))
    
    A4 = arccosd(cos2t)
    theta = calcTheta(ki, kf, A4)
    A3 = om + ss*theta + A3Off
    A3 = np.mod(A3 + ss*180.0,360.0) - ss*180.0
    
    return A3,A4,sgu,sgl
    

def calcTasMisalignment(UB,planeNormal,qe):
    R = buildRMatrix(UB,planeNormal, qe[:3])
    om = arctan2d(R[1,0], R[0,0])
    return om


def calcTasQH(UBINV,angles,Ei,Ef):

  A3,A4 = angles
  r = [0,0,0,A3,A4,0.0,0.0,Ei,Ef]
  
  ki = np.sqrt(Ei)*factorsqrtEK
  kf = np.sqrt(Ef)*factorsqrtEK
  
  QV = calcTasUVectorFromAngles(r);
  
  q = np.sqrt(ki**2 +kf**2-
           2. *ki *kf * cosd(A4));
  
  if len(QV.shape)>2: # If multidimensional QV
    q = np.expand_dims(np.swapaxes(q,0,2),3)

  QV *=q
  
  Q = np.einsum('ij,...j->...i',UBINV,QV)
  
  if len(QV.shape)>2:
    QxQy = np.swapaxes(QV,0,2)
    return Q,QxQy[:,:,:,0],QxQy[:,:,:,1]

  return Q,QV