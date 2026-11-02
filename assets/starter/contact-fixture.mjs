import {Scene} from './geometry.mjs';
const tones={light:'#a6cbb6',mid:'#76a88f',dark:'#47735d',under:'#254638'};
const s=new Scene({name:'同色接触检查',size:48,palette:['#173327',...Object.values(tones)],outline:'#173327',deepOutline:'#254638',cameraAngles:[35.264,90]});
s.roundedBox('后块',{center:[-5,-5,13],size:[18,15,26],radius:3,bevel:1,tones});
s.roundedBox('前块',{center:[5,4,7],size:[18,17,14],radius:3,bevel:1,tones});
s.roundedBox('上块',{center:[2,0,25],size:[18,15,12],radius:3,bevel:1,tones});
export default s;
