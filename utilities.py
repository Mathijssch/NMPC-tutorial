from matplotlib.patches import Rectangle
from matplotlib import animation, rc
import numpy as np
import matplotlib.pyplot as plt 
import pprint 

class Animation: 

    def __init__(self, x, u, vehicle_width, vehicle_length, predictions=None): 
        fig, ax = plt.subplots()
        self.fig = fig 
        self.ax = ax 
        self.ax.axis("square")
        
        dx = 0.5*vehicle_width*np.abs(np.sin(x[2,:])) + 0.5*vehicle_length*np.abs(np.cos(x[2,:]))
        dy = 0.5*vehicle_width*np.abs(np.cos(x[2,:])) + 0.5*vehicle_length*np.abs(np.sin(x[2,:]))

        back = x[:2,:] - 0.5*vehicle_length * np.vstack([[np.cos(x[2,:])],
                                                         [np.sin(x[2,:])]])
        self.corner = back + 0.5*vehicle_width * np.vstack([[np.sin(x[2,:])],[-np.cos(x[2,:])]])
        self.pos = x[:2,:]
        self.angle = x[2,:]
        self.frames = x.shape[1]-1
        # -----------------

        right = x[0,:] + dx
        top = x[1,:] + dy
        left = x[0,:] - dx
        bottom = x[1,:] - dy 
        
        pos_min = np.min(np.vstack((left, bottom)), axis=1)
        pos_max = np.max(np.vstack((right, top)), axis=1)

        self.ax.set_xlim(pos_min[0], pos_max[0])
        self.ax.set_ylim(pos_min[1], pos_max[1])

        self.car = Rectangle(self.corner[:,0], vehicle_length, vehicle_width, alpha=0.8)
        self.parking = Rectangle((-0.6*vehicle_length,-0.6*vehicle_width), 1.2*vehicle_length, 1.2*vehicle_width,ec=(0.00,0.15,0.30), fc=(0.00,0.15,0.30,0.2), linewidth=5)

        self.ax.add_patch(self.parking) 
        self.ax.add_patch(self.car)
        
        self.vx = x[3,:] * np.cos(self.angle)
        self.vy = x[3,:] * np.sin(self.angle)
        self.velocity = self.ax.arrow(self.pos[0,0], self.pos[1,0], self.vx[0], self.vy[0], width=0.1, fc="k", ec="k")
        
        self.predictions = predictions 
        if predictions is not None: 
            pred = self.predictions[0]
            self.predicted_trajectory = self.ax.plot(pred[0,:], pred[1,:])

    def animation(self,i):
        self.car.set_xy(self.corner[:,i])
        self.car.angle = self.angle[i]*180/np.pi
        if self.predictions is not None: 
            pred = self.predictions[i]
            self.predicted_trajectory.set_data(pred[0,:], pred[1,:])

        self.velocity.remove()
        self.velocity = self.ax.arrow(self.pos[0,i], self.pos[1,i], self.vx[i], self.vy[i], width=0.1, fc="k", ec="k")
        # self.ax.arrow(self.pos[0,i], self.pos[0,i], self.vx[i], self.vy[i], width=0.1, fc="k", ec="k")
        return (self.car,)

    def build(self, ts):
        anim = animation.FuncAnimation(self.fig, self.animation,
                                frames=self.frames, interval=ts*10**3, 
                                blit=True)
        return anim 


import panocpy as pa
from tempfile import TemporaryDirectory
import os 
import casadi as cs 

def compile_ocp(nlp: dict, bounds: dict):
    name = "mpcproblem"
    f_prob = cs.Function("f", [nlp["x"], nlp["p"]], [nlp["f"]])
    g_prob = cs.Function("g", [nlp["x"], nlp["p"]], [nlp["g"]])
    codegen, n, m, num_p = pa.generate_casadi_problem(name, f_prob, g_prob)

    with TemporaryDirectory(prefix="panoc_") as tmpdir:
        print("temp dir: ", tmpdir)
        cfile = codegen.generate(tmpdir + "/")
        print("c-file: ", cfile)
        # sofile = tmpdir + f"{name}.so"
        sofile = os.path.join(tmpdir, f"{name}.so")
        os.system(f"gcc -fPIC -shared -O3 -march=native {cfile} -o {sofile}")
        print(sofile)
        prob = pa.load_casadi_problem_with_param(sofile, n, m)
  
    prob.C.lowerbound = bounds["lbx"]
    prob.C.upperbound = bounds["ubx"]
    prob.D.lowerbound = bounds["lbg"]
    prob.D.upperbound = bounds["ubg"] 
    return prob 


def print_solver_stats(stats: dict):
    print(f"{stats['status']} - 'δ': {stats['δ']} - 'ε': {stats['ε']} - outer its. {stats['outer_iterations']}")
    
#     pprint.pprint(stats, depth=1)
#     print(
#         f"Solver status:        {stats['status']}\n",
#         f"Elapsed time:         {stats['elapsed_time']}\n",
#         f"Nb. outer iterations: {stats['outer_iterations']}\n",
#         f"Nb. inner iterations: {stats['inner']['iterations']}\n",
#     )