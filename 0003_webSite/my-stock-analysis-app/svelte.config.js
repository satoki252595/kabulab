import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      pages: 'build',  // 生成先
      assets: 'build', // 生成先
      fallback: 'index.html'
    }),
  }
};