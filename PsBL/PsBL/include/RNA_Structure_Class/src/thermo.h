
#if !defined(THERMO_H)
#define THERMO_H


#include "defines.h"


struct thermo //this structure contains the DH and DS values for helical stacks

{
	char DH[maxfil],DS[maxfil],HELIX[maxfil];
 	short int dh[5][5][5][5];
   short int ds[5][5][5][5];
   short int dhi,dsi,dss; //initiation dh and ds and the ds penalty for symmetry
   short int dha,dsa; //dh and ds penalty for terminal AU pair
   int read();
   thermo(const char *path = 0); //path is a path to the datafiles

};

#endif
