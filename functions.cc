
double mySinh(double *x, double *par)
{
    double x1 = x[0]*par[0];
    double x3 = x1*x1*x1;
    double x5 = x3*x1*x1;
    double x7 = x5*x1*x1;
    double x9 = x7*x1*x1;
    double x11 = x9*x1*x1;
    
    // taylor expansion of sinh:
    //double thefunc = par[1]*(x1 + (x3/6.) + (x5/120.) + (x7/5040.) + (x9/362880.)); // + O(x)^11
    double thefunc = par[1]*( (x11/39916800.) + (x9/362880.) + (x7/5040.) + (x5/120.) + (x3/6.) + x1 ) + par[2]; // + O(x)^13
    
    return thefunc;
}



// double mySinh(double *x, double *par)
// {
//     double x1 = x[0];
//     double x3 = x1*x1*x1;
//     double x5 = x1*x1*x1*x1*x1;
//     double x7 = x1*x1*x1*x1*x1*x1*x1;
//     double x9 = x1*x1*x1*x1*x1*x1*x1*x1*x1;
//     double x11 = x1*x1*x1*x1*x1*x1*x1*x1*x1*x1*x1;
//     
//     // include (x) parameter:    
//     x1 = x1*par[0];
//     x3 = x3*par[0]*par[0]*par[0];
//     x5 = x5*par[0]*par[0]*par[0]*par[0]*par[0];
//     x7 = x7*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0];
//     x9 = x9*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0];
//     x11 = x11*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0]*par[0];
//     
//     // taylor expansion of sinh:
//     //double thefunc = par[1]*(x1 + (x3/6.) + (x5/120.) + (x7/5040.) + (x9/362880.)); // + O(x)^11
//     double thefunc = par[1]*( (x11/39916800.) + (x9/362880.) + (x7/5040.) + (x5/120.) + (x3/6.) + x1 ) + par[2]; // + O(x)^13
//     
//     return thefunc;
// }

// double myRealSinh(double *x, double *par)
// {
//     // for comparison...
//     return par[1]*(exp(par[0]*x[0]) - exp(-par[0]*x[0]));
// }
