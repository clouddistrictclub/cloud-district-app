import axios from 'axios';

const API_URL = 'http://localhost:8001/api';

// Sample placeholder image (1x1 transparent PNG in base64)
const placeholderImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

const sampleProducts = [
  {
    name: 'Geek Bar Pulse X',
    brand: 'Geek Bar',
    category: 'geek-bar',
    image: placeholderImage,
    puffCount: 25000,
    flavor: 'Watermelon Ice',
    nicotinePercent: 5.0,
    price: 24.99,
    stock: 15
  },
  {
    name: 'Lost Mary OS5000',
    brand: 'Lost Mary',
    category: 'lost-mary',
    image: placeholderImage,
    puffCount: 5000,
    flavor: 'Blue Razz Ice',
    nicotinePercent: 5.0,
    price: 19.99,
    stock: 20
  },
  {
    name: 'RAZ TN9000',
    brand: 'RAZ',
    category: 'raz',
    image: placeholderImage,
    puffCount: 9000,
    flavor: 'Strawberry Kiwi',
    nicotinePercent: 5.0,
    price: 21.99,
    stock: 12
  },
  {
    name: 'Meloso Ultra',
    brand: 'Meloso',
    category: 'meloso',
    image: placeholderImage,
    puffCount: 10000,
    flavor: 'Peach Mango',
    nicotinePercent: 5.0,
    price: 22.99,
    stock: 8
  },
  {
    name: 'Digiflavor DROP',
    brand: 'Digiflavor',
    category: 'digiflavor',
    image: placeholderImage,
    puffCount: 7000,
    flavor: 'Mint Ice',
    nicotinePercent: 5.0,
    price: 20.99,
    stock: 10
  },
  {
    name: 'Geek Bar B5000',
    brand: 'Geek Bar',
    category: 'best-sellers',
    image: placeholderImage,
    puffCount: 5000,
    flavor: 'Grape Ice',
    nicotinePercent: 5.0,
    price: 18.99,
    stock: 25
  }
];

async function seedProducts() {
  console.log('Starting product seeding...\n');

  try {
    // Step 1: Register an admin user
    console.log('1. Creating admin user...');
    let token;
    try {
      const registerResponse = await axios.post(`${API_URL}/auth/register`, {
        email: 'admin@clouddistrictclub.com',
        password: 'Admin123!',
        firstName: 'Admin',
        lastName: 'User',
        dateOfBirth: '1990-01-01'
      });
      token = registerResponse.data.access_token;
      console.log('✅ Admin user created');
    } catch (error: any) {
      if (error.response?.status === 400) {
        console.log('Admin user already exists, logging in...');
        const loginResponse = await axios.post(`${API_URL}/auth/login`, {
          email: 'admin@clouddistrictclub.com',
          password: 'Admin123!'
        });
        token = loginResponse.data.access_token;
        console.log('✅ Logged in as admin');
      } else {
        throw error;
      }
    }

    // Step 2: Manually set admin flag (you'll need to do this in MongoDB)
    console.log('\n⚠️  IMPORTANT: Run this MongoDB command to make the user admin:');
    console.log('db.users.updateOne({email: "admin@clouddistrictclub.com"}, {$set: {isAdmin: true}})');
    console.log('\nPress Ctrl+C after running the command, then run this script again.\n');

    // Step 3: Add products
    console.log('2. Adding sample products...');
    let successCount = 0;
    for (const product of sampleProducts) {
      try {
        await axios.post(`${API_URL}/products`, product, {
          headers: { Authorization: `Bearer ${token}` }
        });
        console.log(`✅ Added: ${product.name}`);
        successCount++;
      } catch (error: any) {
        if (error.response?.status === 403) {
          console.log('\n❌ Admin access denied. Please set isAdmin=true in MongoDB first.');
          console.log('Run: db.users.updateOne({email: "admin@clouddistrictclub.com"}, {$set: {isAdmin: true}})');
          break;
        }
        console.log(`❌ Failed to add ${product.name}: ${error.message}`);
      }
    }

    console.log(`\n✅ Successfully added ${successCount} products!`);
    console.log('\nAdmin credentials:');
    console.log('Email: admin@clouddistrictclub.com');
    console.log('Password: Admin123!');
    
  } catch (error: any) {
    console.error('❌ Error:', error.response?.data || error.message);
  }
}

seedProducts();
