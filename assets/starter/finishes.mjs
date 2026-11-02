// Coordinated flat-shaded finish ramps; color finishes, not PBR textures.
export function furnitureFinishes(primary,accent=null){
 const ramps=[
  ['walnut','胡桃木',['#b58b68','#896043','#5d4030','#382a24'],['#e0caa4','#bea17b','#8b7355','#594a38']],
  ['cream','奶油白',['#f4ead2','#d8ccb2','#aaa08b','#766b59'],['#e5c28e','#bc925f','#89643f','#5b432e']],
  ['mint','薄荷绿',['#b8d7bd','#8fb597','#5c8069','#365345'],['#f1dfb7','#cbb58b','#998561','#63553d']],
  ['cobalt','雾霭蓝',['#a7bfd9','#7795b8','#4c6587','#303f58'],['#e9d6ad','#c7ac7e','#91764f','#5d4933']],
  ['terracotta','陶土红',['#e4aa8e','#c58268','#8b5545','#57372f'],['#f0dabc','#ccb08d','#997c5d','#66503a']],
  ['charcoal','炭黑木',['#77736b','#55534e','#393b38','#242824'],['#d5b27c','#ac8755','#7a5b38','#4d3b29']]
 ];
 return ramps.map(([id,name,body,detail])=>{const colors={};for(const [i,k] of ['light','mid','dark','under'].entries()){colors[primary[k]]=body[i];if(accent)colors[accent[k]]=detail[i];}return {id,name,swatches:[body[0],accent?detail[0]:body[2]],colors};});
}
