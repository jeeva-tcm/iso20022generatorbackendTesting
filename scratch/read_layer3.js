const fs = require('fs');
const content = fs.readFileSync('c:/Users/HP/Desktop/iso final/iso20022generatorbackend/app/services/layer3_validator.py', 'utf8');

const lines = content.split('\n');
lines.forEach((line, idx) => {
  if (line.includes('ChrgsInf') || line.includes('InstdAmt') || line.includes('charges')) {
    console.log(`${idx + 1}: ${line.trim()}`);
    // print 3 lines around it
    for (let i = Math.max(0, idx - 2); i < Math.min(lines.length, idx + 3); i++) {
      console.log(`   ${i + 1}: ${lines[i]}`);
    }
  }
});
