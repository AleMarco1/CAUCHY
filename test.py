from astropy.io import fits
hdu = fits.open('data/raw/desi/BGS_BRIGHT-21.5_NGC_0_clustering.dat.fits')
print(hdu.info())
print(hdu[1].columns.names)
print(f"N galassie: {len(hdu[1].data)}")
hdu2 = fits.open('data/raw/desi/BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits')
print(f"N randoms:  {len(hdu2[1].data)}")