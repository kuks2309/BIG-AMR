"""우리 생산 휠 오도(driver_node 경로) vs 레거시 산식 — 궤적 누적 차이 정량화.

실행: python3 Tools/seer_re/odo_oracle/compare_production.py

레거시 산식은 seer_odom_core 로 원본과 비트 대조를 마쳤으므로 여기서는 그 규칙을
파이썬으로 그대로 옮겨 기준자로 쓴다(대조된 규칙: end-point 회전 + floor 정규화).
"""
import math

W1, W2 = (0.6039, 0.0), (-0.5961, 0.0)

def solve_ours(meas, node_xy):
    s_n=s_y=s_x=s_xx_yy=b1=b2=b3=0.0
    for n,(v,th) in meas.items():
        xi,yi=node_xy[n]; mx=v*math.cos(th); my=v*math.sin(th)
        s_n+=1.0; s_y+=yi; s_x+=xi; s_xx_yy+=xi*xi+yi*yi
        b1+=mx; b2+=my; b3+=-yi*mx+xi*my
    a11,a13=s_n,-s_y; a22,a23=s_n,s_x; a33=s_xx_yy
    det=a11*(a22*a33-a23*a23)-a13*(a13*a22)
    vx=((a22*a33-a23*a23)*b1+(a13*a23)*b2+(-a13*a22)*b3)/det
    vy=((a13*a23)*b1+(a11*a33-a13*a13)*b2+(-a11*a23)*b3)/det
    wz=((-a13*a22)*b1+(-a11*a23)*b2+(a11*a22)*b3)/det
    return vx,vy,wz

def normalize(x):
    pi=math.pi
    if not (x < -pi or x >= pi): return x
    tp=pi+pi
    r=x-tp*math.floor(x/tp); y=r if r<pi else r-tp
    return y+tp if y<-pi else y

def run(steps, ds, ang, endpoint):
    """endpoint=True → 레거시(각 먼저 갱신 후 회전), False → 우리 현행(갱신 전 각)."""
    node_xy={1:W1, 2:W2}
    x=y=yaw=0.0
    for _ in range(steps):
        meas={1:(ds[0],ang[0]), 2:(ds[1],ang[1])}
        dx,dy,dyaw=solve_ours(meas,node_xy)
        if endpoint:
            yaw=normalize(yaw+dyaw)
            c,s=math.cos(yaw),math.sin(yaw)
            x+=c*dx-s*dy; y+=s*dx+c*dy
        else:
            c,s=math.cos(yaw),math.sin(yaw)
            x+=c*dx-s*dy; y+=s*dx+c*dy
            yaw=yaw+dyaw
    return x,y,yaw

print("궤적 누적 — 레거시(end-point) vs 현행(start-point)\n")
print(f"{'시나리오':<26}{'경로길이':>9}{'위치차[m]':>12}{'yaw차[deg]':>12}{'상대오차':>10}")
cases=[
    ("호 완만 (조향 ±2°)",  2000, (0.005,0.005), (0.035,-0.035)),
    ("호 보통 (조향 ±8.6°)",2000, (0.005,0.005), (0.15,-0.15)),
    ("호 급 (조향 ±20°)",   2000, (0.005,0.005), (0.35,-0.35)),
    ("제자리 스핀 90°",      500, (0.003,-0.003),(math.pi/2,math.pi/2)),
    ("직진",               2000, (0.005,0.005), (0.0,0.0)),
]
for name,n,ds,ang in cases:
    ax,ay,ayaw=run(n,ds,ang,True)
    bx,by,byaw=run(n,ds,ang,False)
    dpos=math.hypot(ax-bx,ay-by)
    dyawd=math.degrees(abs(normalize(ayaw-byaw)))
    path=n*abs(ds[0])
    rel=dpos/path*100 if path>0 else 0.0
    print(f"{name:<26}{path:>9.1f}{dpos:>12.4f}{dyawd:>12.4f}{rel:>9.2f}%")
